#!/usr/bin/env python3
"""Descarga los pósters de data/posters.csv a web/img/ SIN necesitar la base de datos.
Lo ejecuta GitHub Actions (workflow "Descargar pósters"); también se puede lanzar en local.

- Salta los pósters que ya existen en web/img/ (se puede repetir sin problema).
- Si existe web/img/originales/<id>.jpg|png|webp (subida manual), usa ese archivo en vez del enlace.
- Escribe data/posters_informe.csv con lo que ha ido bien y lo que ha fallado y por qué.
- Actualiza el campo "poster" de web/data/obras.json.

Uso: python tools/posters_ci.py [--pausa 1] [--limite 5] [--csv RUTA] [--web RUTA]
"""
import argparse, csv, json, sys, time
from pathlib import Path

import requests
from PIL import UnidentifiedImageError

sys.path.insert(0, str(Path(__file__).resolve().parent))
from descargar_imagenes import descargar, optimizar, original_local  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", default=str(RAIZ / "data" / "posters.csv"))
    ap.add_argument("--web", default=str(RAIZ / "web"))
    ap.add_argument("--informe", default=str(RAIZ / "data" / "posters_informe.csv"))
    ap.add_argument("--pausa", type=float, default=1.0)
    ap.add_argument("--limite", type=int, default=0)
    a = ap.parse_args()

    web = Path(a.web)
    img = web / "img"
    manuales = img / "originales"
    filas = list(csv.DictReader(open(a.csv, encoding="utf-8")))
    if a.limite:
        filas = filas[:a.limite]

    informe, ok, saltadas, fallos = [], 0, 0, 0
    for f in filas:
        oid, url = int(f["id"]), f["url"]
        if (img / f"{oid}_300.webp").exists() and (img / f"{oid}_600.webp").exists():
            saltadas += 1
            continue
        try:
            local = original_local(manuales, oid) if manuales.exists() else None
            if local:
                datos, origen = local.read_bytes(), "archivo manual"
            else:
                datos, origen = descargar(url), "descargada"
                time.sleep(a.pausa)
            formato, w, h = optimizar(datos, img, oid)
            estado, detalle = "ok", f"{origen}, {formato} {w}x{h}"
            ok += 1
        except requests.HTTPError as e:
            estado, detalle, fallos = "enlace_roto", f"HTTP {e.response.status_code}", fallos + 1
        except (UnidentifiedImageError, ValueError) as e:
            texto = str(e) if isinstance(e, ValueError) and not isinstance(e, UnidentifiedImageError) else "el enlace no devuelve una imagen válida"
            estado, detalle, fallos = "no_es_imagen", texto[:120], fallos + 1
        except (requests.RequestException, OSError) as e:
            estado, detalle, fallos = "error_red", str(e)[:120], fallos + 1
        informe.append([oid, f["titulo"], url, estado, detalle])

    # Marca en obras.json qué obras tienen imagen
    ruta_json = web / "data" / "obras.json"
    if ruta_json.exists():
        d = json.loads(ruta_json.read_text(encoding="utf-8"))
        for o in d["obras"]:
            tiene = (img / f"{o['id']}_300.webp").exists() and (img / f"{o['id']}_600.webp").exists()
            o["poster"] = str(o["id"]) if tiene else None
        ruta_json.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")

    Path(a.informe).parent.mkdir(parents=True, exist_ok=True)
    with open(a.informe, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "titulo", "url_origen", "estado", "detalle"])
        w.writerows(informe)
    print(f"Pósters: {ok} nuevos, {saltadas} ya estaban, {fallos} con problemas -> {a.informe}")


if __name__ == "__main__":
    main()
