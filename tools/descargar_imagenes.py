#!/usr/bin/env python3
"""Descarga los pósters, los guarda en local y los optimiza para la web.

Para cada obra sin imagen alojada:
  1. Si existe originales/<id>.<ext> (subida manual), usa ese archivo.
  2. Si no, lo descarga de poster_origen.
  3. Guarda el original en originales/ (copia de seguridad, no se sube a GitHub).
  4. Genera web/img/<id>_300.webp (tarjetas) y web/img/<id>_600.webp (ficha).
  5. Anota poster_archivo = <id> en la base de datos.

Se puede interrumpir y repetir: solo trabaja con lo que falta.
Todo queda registrado en informes/imagenes.csv (qué falló y por qué).

Uso:
    python tools/descargar_imagenes.py
    python tools/descargar_imagenes.py --solo-publicables --pausa 1
    python tools/descargar_imagenes.py --limite 5          # prueba rápida

Imágenes que fallan o faltan: guarda el archivo como originales/<id>.jpg
(el id lo ves en informes/imagenes.csv) y vuelve a ejecutar el script.
"""
import argparse, csv, io, sqlite3, sys, time
from pathlib import Path

import requests
from PIL import Image, UnidentifiedImageError

RAIZ = Path(__file__).resolve().parent.parent
MAX_BYTES = 15 * 1024 * 1024
ANCHOS = (300, 600)
CABECERAS = {"User-Agent": "Mozilla/5.0 (compatible; Safoteca-catalogo/1.0; proyecto sin animo de lucro)"}
EXTENSIONES = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif")


def original_local(carpeta: Path, oid: int):
    for ext in EXTENSIONES:
        p = carpeta / f"{oid}{ext}"
        if p.exists():
            return p
    return None


def descargar(url: str) -> bytes:
    with requests.get(url, headers=CABECERAS, timeout=(10, 30), stream=True, allow_redirects=True) as r:
        r.raise_for_status()
        trozos, total = [], 0
        for t in r.iter_content(65536):
            total += len(t)
            if total > MAX_BYTES:
                raise ValueError("la imagen supera 15 MB")
            trozos.append(t)
    return b"".join(trozos)


def optimizar(datos: bytes, destino: Path, oid: int):
    """Devuelve (formato_original, ancho, alto). Lanza excepción si no es una imagen válida."""
    img = Image.open(io.BytesIO(datos))
    img.verify()
    img = Image.open(io.BytesIO(datos))  # verify() invalida el objeto
    formato, (ancho, alto) = img.format, img.size
    if ancho < 50 or alto < 50:
        raise ValueError(f"imagen demasiado pequeña ({ancho}x{alto})")
    img = img.convert("RGBA" if "A" in img.getbands() else "RGB")
    destino.mkdir(parents=True, exist_ok=True)
    for w in ANCHOS:
        nuevo_w = min(w, ancho)  # nunca se amplía
        nuevo_h = round(alto * nuevo_w / ancho)
        img.resize((nuevo_w, nuevo_h), Image.LANCZOS).save(destino / f"{oid}_{w}.webp", "WEBP", quality=80, method=6)
    return formato, ancho, alto


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default=str(RAIZ / "safoteca.db"))
    ap.add_argument("--originales", default=str(RAIZ / "originales"))
    ap.add_argument("--salida", default=str(RAIZ / "web" / "img"))
    ap.add_argument("--informe", default=str(RAIZ / "informes" / "imagenes.csv"))
    ap.add_argument("--solo-publicables", action="store_true", help="solo películas y series")
    ap.add_argument("--pausa", type=float, default=0.5, help="segundos entre descargas (cortesía con los servidores)")
    ap.add_argument("--limite", type=int, default=0)
    a = ap.parse_args()

    orig, salida = Path(a.originales), Path(a.salida)
    orig.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(a.db)
    filtro = "AND tipo IN ('pelicula','serie')" if a.solo_publicables else ""
    pendientes = db.execute(
        f"SELECT id, titulo_original, poster_origen FROM obra WHERE poster_archivo IS NULL {filtro} ORDER BY id").fetchall()
    if a.limite:
        pendientes = pendientes[:a.limite]

    informe, ok, fallos = [], 0, 0
    print(f"{len(pendientes)} obras sin imagen alojada")
    for i, (oid, titulo, url) in enumerate(pendientes, 1):
        estado = detalle = ""
        try:
            local = original_local(orig, oid)
            if local:
                datos, origen = local.read_bytes(), "archivo manual"
            elif url:
                datos, origen = descargar(url), "descargada"
                time.sleep(a.pausa)
            else:
                informe.append([oid, titulo, "", "sin_imagen", "no hay póster ni archivo manual originales/%d.jpg" % oid])
                fallos += 1
                continue
            formato, w, h = optimizar(datos, salida, oid)
            if not local:
                ext = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp", "GIF": ".gif"}.get(formato, ".img")
                (orig / f"{oid}{ext}").write_bytes(datos)
            db.execute("UPDATE obra SET poster_archivo = ? WHERE id = ?", (str(oid), oid))
            db.commit()
            estado, detalle = "ok", f"{origen}, {formato} {w}x{h}"
            ok += 1
        except requests.HTTPError as e:
            estado, detalle, fallos = "enlace_roto", f"HTTP {e.response.status_code}", fallos + 1
        except (UnidentifiedImageError, ValueError) as e:
            texto = str(e) if isinstance(e, ValueError) and not isinstance(e, UnidentifiedImageError) else "el archivo no es una imagen válida"
            estado, detalle, fallos = "no_es_imagen", texto[:120], fallos + 1
        except (requests.RequestException, OSError) as e:
            estado, detalle, fallos = "error_red", str(e)[:120], fallos + 1
        informe.append([oid, titulo, url or "", estado, detalle])
        if i % 20 == 0:
            print(f"  {i}/{len(pendientes)}  ok={ok} fallos={fallos}")

    Path(a.informe).parent.mkdir(parents=True, exist_ok=True)
    with open(a.informe, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "titulo", "url_origen", "estado", "detalle"])
        w.writerows(informe)
    print(f"\nTerminado: {ok} correctas, {fallos} con problemas -> {a.informe}")
    if fallos:
        print("Para las que fallan: guarda la imagen como originales/<id>.jpg y vuelve a ejecutar.")


if __name__ == "__main__":
    main()
