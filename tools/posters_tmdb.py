#!/usr/bin/env python3
"""Candidatos de TMDB para cambiar pósters de baja calidad (no cambia nada en la base de datos).

Para cada obra de la lista busca en TMDB hasta 3 pósters verticales de 600 px de ancho o más:
el mejor en español, el mejor en inglés y el mejor en el idioma original de la obra.
Escribe <salida>/candidatos.csv y una miniatura de cada uno (<salida>/miniaturas/<id>_<n>.webp, 200 px)
para revisarlos al lado del póster actual.

Uso (necesita TMDB_TOKEN): python tools/posters_tmdb.py --ids 1,4,6 --salida revision_posters
"""
import argparse, csv, io, os, sqlite3, sys, urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rutas import DB_DEFECTO  # noqa: E402
from fechas_tmdb import TMDB  # noqa: E402

IMG = "https://image.tmdb.org/t/p/"
IDIOMAS = "es,en,null,ja,ko,th,zh,fr,de,it,pt,sv,no,da,nl,pl,fi,he,tl,id,ca"


def mejor(posters, idioma):
    buenos = [p for p in posters if p.get("iso_639_1") == idioma and (p.get("width") or 0) >= 600
              and 1.35 <= (p.get("height") or 0) / max(p.get("width") or 1, 1) <= 1.6]
    return max(buenos, key=lambda p: (p.get("vote_average") or 0, p.get("vote_count") or 0, p.get("width") or 0), default=None)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ids", required=True, help="ids de La Safoteca separados por comas")
    ap.add_argument("--salida", default="revision_posters")
    a = ap.parse_args()
    token = os.environ.get("TMDB_TOKEN", "").strip()
    if not token:
        sys.exit("Falta la variable TMDB_TOKEN.")
    from PIL import Image
    api = TMDB(token)
    sal = Path(a.salida)
    (sal / "miniaturas").mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_DEFECTO)
    filas, sin = [], []
    for oid in [int(x) for x in a.ids.replace(" ", "").split(",") if x.strip().isdigit()]:
        r = db.execute("SELECT coalesce(titulo_es, titulo_original), tmdb_id FROM obra WHERE id = ?", (oid,)).fetchone()
        if not r or not r[1]:
            sin.append((oid, r[0] if r else "?", "sin tmdb_id"))
            continue
        titulo, tid = r
        d = api.get("/" + tid, append_to_response="images", include_image_language=IDIOMAS) or {}
        posters = (d.get("images") or {}).get("posters") or []
        orig = d.get("original_language") or ""
        elegidos = []
        for idioma, nombre in (("es", "español"), ("en", "inglés"), (orig, f"original ({orig})")):
            p = mejor(posters, idioma) if idioma else None
            if p and all(p["file_path"] != e[0]["file_path"] for e in elegidos):
                elegidos.append((p, nombre))
        if not elegidos:
            sin.append((oid, titulo, f"TMDB no tiene pósters de 600 px o más ({len(posters)} en total)"))
            continue
        for n, (p, nombre) in enumerate(elegidos, 1):
            with urllib.request.urlopen(IMG + "w342" + p["file_path"], timeout=30) as resp:
                im = Image.open(io.BytesIO(resp.read())).convert("RGB")
            im.resize((200, round(im.height * 200 / im.width)), Image.LANCZOS).save(sal / "miniaturas" / f"{oid}_{n}.webp", "WEBP", quality=75)
            filas.append([oid, titulo, tid, n, nombre, p["width"], p["height"], IMG + "original" + p["file_path"]])
        print(f"  {oid} · {titulo}: {len(elegidos)} candidato(s)")
    with open(sal / "candidatos.csv", "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "título", "tmdb", "n", "idioma", "ancho", "alto", "url"])
        w.writerows(filas)
    with open(sal / "sin_candidato.csv", "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "título", "motivo"])
        w.writerows(sin)
    print(f"Obras con candidatos: {len({f[0] for f in filas})} · candidatos: {len(filas)} · sin candidato: {len(sin)} · llamadas: {api.llamadas}")
    for s in sin:
        print(f"  - {s[0]} · {s[1]}: {s[2]}")


if __name__ == "__main__":
    main()
