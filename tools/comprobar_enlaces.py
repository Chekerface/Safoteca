#!/usr/bin/env python3
"""Comprueba los enlaces de «dónde ver» de web/data/obras.json.

Uso:  python3 tools/comprobar_enlaces.py [--salida informes/enlaces.csv] [--hilos 8]

Estados:
  OK          la página responde y no redirige a la portada
  ROTO        404/410/5xx, redirige a la portada, o es una URL de búsqueda
  PIRATA      dominio de streaming no oficial (conviene quitarlo)
  BLOQUEADO   la web no deja comprobarlo de forma automática (403/429…): revisar a mano
  ERROR       no se pudo conectar (dominio caído, tiempo agotado)

Solo usa la biblioteca estándar. Pensado para ejecutarse en GitHub Actions
(.github/workflows/enlaces.yml), donde sí hay acceso a internet.
"""
import argparse, csv, json, re, sys, urllib.error, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlparse

RAIZ = Path(__file__).resolve().parent.parent
PIRATAS = ("cuevana", "gnula", "hdfull", "animeflv", "animeonline", "peliculasflv", "flixole",
           "mega1080p", "fdrama", "theowlclub", "pelisplus", "repelis", "seriesflv")
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0 Safari/537.36")


def es_portada(url):
    """True si la ruta es la raíz o solo un código de idioma (/es, /es/es, /es-es…)."""
    partes = [p for p in urlparse(url).path.split("/") if p]
    return all(re.fullmatch(r"[a-z]{2}(-[a-z]{2})?", p, re.I) for p in partes)


def comprobar(url):
    host = urlparse(url).netloc.lower()
    if any(p in host for p in PIRATAS):
        return "PIRATA", "dominio no oficial"
    if "/search" in urlparse(url).path:
        return "ROTO", "es una búsqueda, no una ficha"
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "es-ES,es;q=0.9"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            final = r.geturl()
            if not es_portada(url) and es_portada(final):
                return "ROTO", f"redirige a la portada ({final})"
            return "OK", ""
    except urllib.error.HTTPError as e:
        if e.code in (404, 410) or e.code >= 500:
            return "ROTO", f"HTTP {e.code}"
        return "BLOQUEADO", f"HTTP {e.code}"
    except Exception as e:  # DNS, tiempo agotado, TLS…
        return "ERROR", type(e).__name__


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--salida", default=str(RAIZ / "informes" / "enlaces.csv"))
    ap.add_argument("--hilos", type=int, default=8)
    a = ap.parse_args()
    datos = json.load(open(RAIZ / "web" / "data" / "obras.json", encoding="utf-8"))
    obras = datos["obras"] if isinstance(datos, dict) else datos
    tareas = [(o["id"], o["titulo"], u) for o in obras for u in (o.get("donde_ver") or [])]
    with ThreadPoolExecutor(a.hilos) as ex:
        res = list(ex.map(lambda t: comprobar(t[2]), tareas))
    filas = [[i, t, u, e, m] for (i, t, u), (e, m) in zip(tareas, res)]
    Path(a.salida).parent.mkdir(parents=True, exist_ok=True)
    with open(a.salida, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f); w.writerow(["id", "titulo", "url", "estado", "motivo"]); w.writerows(filas)
    cuenta = {}
    for f in filas: cuenta[f[3]] = cuenta.get(f[3], 0) + 1
    print(f"{len(filas)} enlaces:", ", ".join(f"{k} {v}" for k, v in sorted(cuenta.items())))
    sin = [o for o in obras if not o.get("donde_ver")]
    print(f"{len(sin)} obras sin enlace")
    for f in filas:
        if f[3] in ("ROTO", "PIRATA"): print(f"  {f[3]}: {f[0]} {f[1]} -> {f[2]} ({f[4]})")
    # código de salida 1 si hay enlaces rotos o piratas (el workflow abre una incidencia)
    return 1 if any(f[3] in ("ROTO", "PIRATA") for f in filas) else 0


if __name__ == "__main__":
    sys.exit(main())
