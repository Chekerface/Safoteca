#!/usr/bin/env python3
"""Informe (no cambia nada): ¿qué fecha de estreno en ESPAÑA tiene TMDB para cada película?

TMDB guarda, para cada película, sus estrenos por país (release_dates) con un tipo:
1 premiere (festival) · 2 cines (limitado) · 3 cines · 4 digital (plataforma) · 5 físico · 6 TV.
Para España se toma el primer estreno de tipo 2, 3, 4 o 6 (no los festivales).
Las series no tienen fecha por país en TMDB: se quedan fuera.

Uso (necesita TMDB_TOKEN): python tools/fechas_espana.py
Escribe informes/fechas_espana.csv y un resumen por pantalla.
"""
import csv, os, sqlite3, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rutas import DB_DEFECTO  # noqa: E402
from fechas_tmdb import TMDB, RAIZ  # noqa: E402

TIPOS = {1: "festival", 2: "cines (limitado)", 3: "cines", 4: "digital", 5: "físico", 6: "TV"}


def main():
    token = os.environ.get("TMDB_TOKEN", "").strip()
    if not token:
        sys.exit("Falta la variable TMDB_TOKEN.")
    api = TMDB(token)
    db = sqlite3.connect(DB_DEFECTO)
    db.row_factory = sqlite3.Row
    pelis = db.execute("SELECT id, coalesce(titulo_es, titulo_original) t, anio, tmdb_id, fecha_estreno FROM obra "
                       "WHERE tipo = 'pelicula' AND tmdb_id LIKE 'movie/%' ORDER BY id").fetchall()
    filas, n = [], {"con_es": 0, "sin_es": 0, "igual": 0, "distinta": 0}
    for p in pelis:
        d = api.get("/" + p["tmdb_id"] + "/release_dates") or {}
        es = next((r for r in d.get("results", []) if r.get("iso_3166_1") == "ES"), None)
        fechas = sorted(((x.get("release_date") or "")[:10], x.get("type")) for x in (es or {}).get("release_dates", [])
                        if x.get("type") in (2, 3, 4, 6) and x.get("release_date"))
        todas = ", ".join(f"{f} ({TIPOS.get(t, t)})" for f, t in sorted(((x.get("release_date") or "")[:10], x.get("type"))
                                                                       for x in (es or {}).get("release_dates", [])))
        if fechas:
            n["con_es"] += 1
            f_es, tipo = fechas[0]
            if f_es == (p["fecha_estreno"] or ""):
                n["igual"] += 1
                estado = "igual"
            else:
                n["distinta"] += 1
                estado = "DISTINTA"
        else:
            n["sin_es"] += 1
            f_es, tipo, estado = "", None, "sin fecha española en TMDB"
        filas.append([p["id"], p["t"], p["anio"], p["tmdb_id"], p["fecha_estreno"] or "", f_es, TIPOS.get(tipo, ""), estado, todas])
    (RAIZ / "informes").mkdir(exist_ok=True)
    with open(RAIZ / "informes" / "fechas_espana.csv", "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "película", "año", "tmdb", "fecha que tenemos", "fecha en España (TMDB)", "tipo", "comparación",
                    "todos los estrenos en España"])
        w.writerows(sorted(filas, key=lambda r: (r[7] != "DISTINTA", r[7], r[0])))
    total = len(pelis)
    print(f"Películas con TMDB: {total}")
    print(f"  con fecha española en TMDB: {n['con_es']} ({100 * n['con_es'] / max(total, 1):.0f} %)")
    print(f"     · igual que la que tenemos: {n['igual']}")
    print(f"     · distinta: {n['distinta']}")
    print(f"  sin fecha española en TMDB: {n['sin_es']}")
    print("Distintas:")
    for r in filas:
        if r[7] == "DISTINTA":
            print(f"  - {r[0]} · {r[1]} ({r[2]}): tenemos {r[4] or '—'} · España {r[5]} ({r[6]})")
    print(f"Llamadas a TMDB: {api.llamadas}. Detalle: informes/fechas_espana.csv")


if __name__ == "__main__":
    main()
