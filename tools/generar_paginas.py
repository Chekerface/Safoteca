#!/usr/bin/env python3
"""Genera una página HTML sencilla por obra (obra/<id>/index.html) para que los buscadores puedan indexarlas.

No sustituye a la app: es una «puerta de entrada» con título, sinopsis, póster y un botón que abre la ficha
completa en la web normal (#/obra/<id>). Las direcciones de la app no cambian.

Uso (lo lanza el deploy; no hace falta ejecutarlo a mano):
    python3 tools/generar_paginas.py --web web                        # PRO: escribe web/obra/ y añade al sitemap
    python3 tools/generar_paginas.py --web web/uat --noindex          # PRE: mismas páginas, sin indexar
"""
import argparse, html, json, re
from pathlib import Path

DOMINIO = "https://www.lasafoteca.com"
TIPO = {"serie": "Serie", "pelicula": "Película"}
SCHEMA = {"serie": "TVSeries", "pelicula": "Movie"}


def e(s):
    return html.escape(str(s or ""), quote=True)


def recorta(texto, n=155):
    texto = re.sub(r"\s+", " ", texto or "").strip()
    return texto if len(texto) <= n else texto[: n - 1].rsplit(" ", 1)[0] + "…"


def niveles(web):
    cfg = (web / "config.js").read_text(encoding="utf-8")
    return {k: (re.search(rf'\b{k}:\s*"([^"]+)"', cfg) or [None, ""])[1] for k in "ABC"}


def anios(o):
    if o.get("anio_fin") and o["anio_fin"] != o.get("anio"):
        return f'{o["anio"]}–{o["anio_fin"]}'
    return str(o.get("anio") or "")


def pagina(o, nivel, noindex):
    oid, tit = o["id"], o["titulo"]
    url = f"{DOMINIO}/obra/{oid}/"
    tipo = TIPO.get(o["tipo"], "Obra")
    datos = " · ".join(x for x in [tipo, o.get("pais"), anios(o)] if x)
    desc = recorta(f'{tipo} con representación lésbica o bisexual. {o.get("sinopsis") or ""}')
    img = f"../../img/{e(o['poster'])}_600.webp" if o.get("poster") else ""
    img_abs = f"{DOMINIO}/img/{o['poster']}_600.webp" if o.get("poster") else f"{DOMINIO}/icons/icon-512.png"
    n_av = len(o.get("avisos") or [])
    avisos = ("Esta obra no tiene avisos de contenido." if not n_av else
              f"Esta obra tiene {n_av} aviso{'s' if n_av != 1 else ''} de contenido. "
              "En la ficha completa están ocultos hasta que decidas verlos, para no destriparte nada.")
    ld = {"@context": "https://schema.org", "@type": SCHEMA.get(o["tipo"], "CreativeWork"), "name": tit,
          "url": url, "inLanguage": "es", "image": img_abs}
    if o.get("titulo_original") and o["titulo_original"] != tit:
        ld["alternateName"] = o["titulo_original"]
    if o.get("anio"):
        ld["datePublished"] = str(o["anio"])
    if o.get("sinopsis"):
        ld["description"] = recorta(o["sinopsis"], 500)
    if o.get("generos"):
        ld["genre"] = o["generos"]
    if o.get("pais"):
        ld["countryOfOrigin"] = {"@type": "Country", "name": o["pais"]}
    if o.get("directores"):
        ld["director"] = [{"@type": "Person", "name": p} for p in o["directores"]]
    if o.get("actrices"):
        ld["actor"] = [{"@type": "Person", "name": p} for p in o["actrices"]]
    plataformas = sorted({p["n"] for p in (o.get("plataformas") or []) if p.get("n")})
    filas = [("Título original", o.get("titulo_original") if o.get("titulo_original") != tit else ""),
             ("Género", ", ".join(o.get("generos") or [])),
             ("Dirección", ", ".join(o.get("directores") or [])),
             ("Reparto", ", ".join(o.get("actrices") or [])),
             ("Temporadas", o.get("temporadas")),
             ("Edad recomendada", f'{o["edad"]}+' if o.get("edad") else ""),
             ("Dónde verla", ", ".join(plataformas))]
    filas_html = "".join(f"<dt>{e(k)}</dt><dd>{e(v)}</dd>" for k, v in filas if v)
    rel = o.get("relevancia")
    rel_html = f'<p class="nivel"><span class="tejuelo">{e(rel)}</span> {e(nivel.get(rel, ""))}</p>' if rel else ""
    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(tit)} ({e(o.get("anio") or "")}) · {e(tipo)} · La Safoteca</title>
<meta name="description" content="{e(desc)}">
{'<meta name="robots" content="noindex, nofollow">' if noindex else ''}
<link rel="canonical" href="{url}">
<meta property="og:type" content="{'video.tv_show' if o['tipo'] == 'serie' else 'video.movie'}">
<meta property="og:site_name" content="La Safoteca">
<meta property="og:title" content="{e(tit)} · La Safoteca">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{e(img_abs)}">
<meta property="og:locale" content="es_ES">
<link rel="icon" href="../../marca/buholira.svg" type="image/svg+xml">
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
<style>
:root{{--lila:#9c88bb;--violeta:#5d4a8a;--tinta:#2a2140;--suave-t:#5f5675;--papel:#fbf9fe;--sup:#fff;--linea:#ddd5ec;--btn:#5d4a8a;--btn-t:#fff;
  --serif:"Iowan Old Style","Palatino Linotype",Palatino,Georgia,serif;--sans:system-ui,-apple-system,"Segoe UI",Roboto,Arial,sans-serif}}
@media (prefers-color-scheme:dark){{:root{{--lila:#b3a2dd;--violeta:#c4b6ea;--tinta:#efeaf8;--suave-t:#b9b0cf;--papel:#16131d;--sup:#201b2b;--linea:#3a3150;--btn:#b3a2dd;--btn-t:#1c1628}}}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--papel);color:var(--tinta);font:16px/1.55 var(--sans)}}
header{{padding:14px 16px;border-bottom:1px solid var(--linea);background:var(--sup)}}
header a{{display:inline-flex;align-items:center;gap:8px;color:var(--tinta);text-decoration:none;font:600 18px var(--serif)}}
header img{{width:30px;height:30px}}
main{{max-width:760px;margin:0 auto;padding:20px 16px 48px;display:grid;gap:18px}}
@media (min-width:640px){{main{{grid-template-columns:240px 1fr;align-items:start}} .cuerpo{{grid-column:2}} .poster{{grid-row:1/span 3}}}}
.poster{{width:100%;max-width:300px;aspect-ratio:2/3;object-fit:cover;border-radius:10px;background:var(--linea);box-shadow:0 6px 18px rgb(42 33 64/.12)}}
h1{{margin:0;font:600 clamp(26px,6vw,34px)/1.15 var(--serif)}}
.datos{{margin:4px 0 0;color:var(--suave-t)}}
.boton{{display:inline-block;background:var(--btn);color:var(--btn-t);text-decoration:none;font-weight:700;padding:14px 20px;border-radius:12px;margin:6px 0}}
.nivel{{display:flex;gap:10px;align-items:flex-start;margin:0}}
.tejuelo{{flex:none;display:inline-grid;place-items:center;width:2rem;height:2.3rem;border-radius:4px 4px 10px 10px;background:var(--lila);color:#fff;font:700 18px var(--serif)}}
.avisos{{background:var(--sup);border:1px solid var(--linea);border-radius:10px;padding:12px 14px;margin:0}}
dl{{display:grid;grid-template-columns:max-content 1fr;gap:6px 14px;margin:0}} dt{{color:var(--suave-t)}} dd{{margin:0}}
footer{{text-align:center;color:var(--suave-t);font-size:14px;padding:0 16px 32px}} footer a{{color:var(--violeta)}}
</style>
</head>
<body>
<header><a href="../../"><img src="../../marca/buholira.svg" alt="">La Safoteca</a></header>
<main>
  {f'<img class="poster" src="{img}" alt="Póster de {e(tit)}" width="300" height="450">' if img else ''}
  <div class="cuerpo">
    <h1>{e(tit)}</h1>
    <p class="datos">{e(datos)}</p>
    <p><a class="boton" href="../../#/obra/{oid}">Ver la ficha completa en La Safoteca</a></p>
  </div>
  <div class="cuerpo">{rel_html}</div>
  <div class="cuerpo" style="display:grid;gap:14px">
    {f'<p style="margin:0">{e(o["sinopsis"])}</p>' if o.get("sinopsis") else ''}
    <p class="avisos">{e(avisos)}</p>
    <dl>{filas_html}</dl>
  </div>
</main>
<footer>La Safoteca: catálogo gratuito de series y películas con representación lésbica y bisexual, con avisos de contenido.<br><a href="../../">Ir al catálogo</a></footer>
</body>
</html>
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--web", required=True, help="carpeta de la web (web o web/uat)")
    ap.add_argument("--noindex", action="store_true", help="marca las páginas para que no se indexen (PRE)")
    ap.add_argument("--sitemap", help="sitemap.xml al que añadir las páginas (solo PRO)")
    a = ap.parse_args()
    web = Path(a.web)
    datos = json.loads((web / "data" / "obras.json").read_text(encoding="utf-8"))
    nivel = niveles(web)
    for o in datos["obras"]:
        d = web / "obra" / str(o["id"])
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(pagina(o, nivel, a.noindex), encoding="utf-8")
    print(f"Páginas por obra: {len(datos['obras'])} en {web / 'obra'}")
    if a.sitemap:
        sm = Path(a.sitemap)
        txt = sm.read_text(encoding="utf-8")
        filas = "".join(f"  <url><loc>{DOMINIO}/obra/{o['id']}/</loc><lastmod>{(o.get('publicada') or '')[:10] or datos['meta']['generado'][:10]}</lastmod></url>\n"
                        for o in datos["obras"])
        sm.write_text(txt.replace("</urlset>", filas + "</urlset>"), encoding="utf-8")
        print(f"Añadidas {len(datos['obras'])} direcciones a {sm}")


if __name__ == "__main__":
    main()
