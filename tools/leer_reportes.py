#!/usr/bin/env python3
"""Resume los avisos de enlaces rotos recibidos por el formulario de «Avisar de un enlace roto».

Uso:
    python tools/leer_reportes.py enlaces_reportados.xlsx              # resumen + informes/enlaces_reportados.csv
    python tools/leer_reportes.py enlaces_reportados.csv --comprobar   # además prueba cada enlace reportado

El archivo se descarga de la hoja de respuestas (Archivo → Descargar → .xlsx o .csv). Los avisos se agrupan por
enlace y se ordenan por número de avisos. Para cada enlace se indica:
  * si sigue en la web (si ya se cambió desde que lo reportaron, sale «ya no está»: no hay nada que hacer),
  * con --comprobar, qué dice la revisión automática (OK, ROTO, BLOQUEADO…; necesita internet),
  * una sugerencia: REVISAR si la comprobación falla o hay 3 o más avisos; VER si tiene avisos pero no hay más
    pruebas; RESUELTO si ya no está.
No modifica la base de datos: la corrección se hace como siempre (plantilla, formulario o a mano).
"""
import argparse, csv, json, re, sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from importar_plantilla import abrir_hoja, leer_filas  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
UMBRAL = 3


def url_clave(u):
    return re.sub(r"^https?://(www\.)?", "", str(u or "").strip().lower()).rstrip("/")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("archivo")
    ap.add_argument("--comprobar", action="store_true", help="prueba cada enlace reportado (necesita internet)")
    ap.add_argument("--salida", default=str(RAIZ / "informes" / "enlaces_reportados.csv"))
    a = ap.parse_args()

    obras = json.load(open(RAIZ / "web" / "data" / "obras.json", encoding="utf-8"))["obras"]
    vigentes = {url_clave(u) for o in obras for u in o.get("donde_ver") or []}

    grupos = defaultdict(lambda: {"id": "", "obra": "", "plat": "", "url": "", "motivos": Counter(), "coment": [], "fechas": []})
    n_filas = 0
    for _, f in leer_filas(abrir_hoja(a.archivo, False)):
        url = str(f.get("enlace") or "").strip()
        if not url:
            continue
        n_filas += 1
        g = grupos[url_clave(url)]
        g["url"] = url
        g["id"] = g["id"] or str(f.get("id de la obra") or "").replace(".0", "")
        g["obra"] = g["obra"] or str(f.get("obra") or "")
        g["plat"] = g["plat"] or str(f.get("plataforma") or "")
        g["motivos"][str(f.get("¿que pasa con el enlace?") or "").strip()] += 1
        c = str(f.get("comentario (opcional)") or "").strip()
        if c:
            g["coment"].append(c)
        if f.get("marca temporal"):
            g["fechas"].append(str(f["marca temporal"]))

    if a.comprobar:
        from comprobar_enlaces import comprobar

    filas = []
    for k, g in grupos.items():
        total = sum(g["motivos"].values())
        vigente = k in vigentes
        auto = ("", "")
        if a.comprobar and vigente:
            auto = comprobar(g["url"])
        if not vigente:
            sug = "RESUELTO"
        elif auto[0] in ("ROTO", "ERROR", "PIRATA") or total >= UMBRAL:
            sug = "REVISAR"
        else:
            sug = "VER"
        filas.append([g["id"], g["obra"], g["plat"], g["url"], total,
                      "; ".join(f"{m} ({n})" for m, n in g["motivos"].most_common()),
                      " | ".join(g["coment"]), "sí" if vigente else "ya no está", auto[0], auto[1],
                      min(g["fechas"]) if g["fechas"] else "", max(g["fechas"]) if g["fechas"] else "", sug])
    orden = {"REVISAR": 0, "VER": 1, "RESUELTO": 2}
    filas.sort(key=lambda r: (orden[r[-1]], -r[4]))

    Path(a.salida).parent.mkdir(parents=True, exist_ok=True)
    with open(a.salida, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "obra", "plataforma", "url", "avisos", "motivos", "comentarios", "sigue en la web",
                    "comprobación", "detalle", "primer aviso", "último aviso", "sugerencia"])
        w.writerows(filas)
    print(f"{n_filas} avisos sobre {len(filas)} enlaces distintos -> {a.salida}")
    for r in filas:
        print(f"  [{r[-1]}] {r[4]}x  id {r[0]} {r[1]} · {r[2]} · {r[3]}  ({r[5]})")


if __name__ == "__main__":
    main()
