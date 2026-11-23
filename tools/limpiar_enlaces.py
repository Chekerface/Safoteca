#!/usr/bin/env python3
"""Limpia los enlaces de rastreo: quita de cada URL lo que no hace falta para llegar a la página
(identificadores de quien compartió, códigos de afiliados, marcas de anuncios, de búsqueda y de origen).

Se conserva solo lo imprescindible de cada web: el vídeo o la lista de YouTube, la ficha de Movistar+,
la búsqueda de Milcomics, el código «gti» de Prime Video cuando es el único código de la obra, y el idioma.

Uso:
    python tools/limpiar_enlaces.py --simular        # informe en informes/enlaces_limpios.csv, sin guardar
    python tools/limpiar_enlaces.py                  # guarda (con copia de la base de datos antes)
Lo usa también el importador para los enlaces nuevos (limpiar()).
"""
import argparse, csv, re, shutil, sqlite3, sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

sys.path.insert(0, str(Path(__file__).resolve().parent))

IDIOMA = {"l", "lang", "language", "hl"}
CONSERVAR = {                        # parámetros imprescindibles por web
    "youtube.com": {"v", "list"}, "youtu.be": set(),
    "movistarplus.es": {"tipo", "id"},
    "milcomics.com": None,           # None = es una búsqueda: se conserva entera
    "play.google.com": {"id"},       # el código de la película va en ?id=
    "rakuten.tv": {"content_type", "content_id"},
}


def _web(host):
    host = host.lower()
    for k in CONSERVAR:
        if host == k or host.endswith("." + k):
            return k
    return host


def limpiar(url):
    url = (url or "").strip()
    if not url.startswith(("http://", "https://")):
        return url
    p = urlsplit(url)
    web = _web(p.netloc)
    ruta = p.path
    if "amazon." in p.netloc or "primevideo.com" in p.netloc:
        ruta = re.sub(r"/ref=[^/]*", "", ruta)                       # /ref=atv_... en mitad de la dirección
        ruta = re.sub(r"^(/-/[a-z]{2})?(/region/[a-z]{2})?(?=/)", "", ruta)  # /-/es/region/eu/detail/... → /detail/...
        ruta = ruta.rstrip("/") or "/"
    pares = parse_qsl(p.query, keep_blank_values=True)
    if CONSERVAR.get(web, "x") is None:
        q = pares
    else:
        deja = set(CONSERVAR.get(web) or ()) | IDIOMA
        if "primevideo.com" in p.netloc and re.fullmatch(r"/(detail|dp)/?", ruta):
            deja |= {"gti"}                                         # el código de la obra va en ?gti=
        q = [(k, v) for k, v in pares if k in deja]
    return urlunsplit((p.scheme, p.netloc, ruta, urlencode(q), ""))


def main():
    from rutas import DB_DEFECTO, COPIAS, RAIZ
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default=str(DB_DEFECTO))
    ap.add_argument("--simular", action="store_true")
    a = ap.parse_args()
    db = sqlite3.connect(a.db)
    cambios = []
    for i, oid, tit, tipo, est, url in db.execute(
            "SELECT e.id, e.obra_id, coalesce(o.titulo_es, o.titulo_original), o.tipo, o.estado, e.url "
            "FROM obra_enlace e JOIN obra o ON o.id = e.obra_id ORDER BY e.obra_id"):
        nueva = limpiar(url)
        if nueva != url:
            cambios.append((i, oid, tit, tipo, est, url, nueva))
    (RAIZ / "informes").mkdir(exist_ok=True)
    with open(RAIZ / "informes" / "enlaces_limpios.csv", "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["id_enlace", "obra", "título", "tipo", "estado", "antes", "después"])
        w.writerows(cambios)
    print(f"Enlaces que cambian: {len(cambios)} (detalle en informes/enlaces_limpios.csv)")
    if a.simular or not cambios:
        return
    copia = COPIAS / f"safoteca_antes_enlaces_{datetime.now():%Y%m%d_%H%M%S}.db"
    copia.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(a.db, copia)
    for i, *_, nueva in cambios:
        db.execute("UPDATE obra_enlace SET url = ? WHERE id = ?", (nueva, i))
    db.commit()
    print("Guardado. Copia previa:", copia)


if __name__ == "__main__":
    main()
