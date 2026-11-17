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


def relacionadas(o, todas, n=6):
    """Las 6 primeras de la lista «rel» de obras.json: la misma fórmula que la web (tools/relacionadas.py)."""
    por_id = {x["id"]: x for x in todas}
    return [por_id[i] for i in (o.get("rel") or []) if i in por_id][:n]


def pagina(o, nivel, noindex, todas=()):
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
             ("Título en Latinoamérica", o.get("titulo_latam") if o.get("titulo_latam") not in (tit, o.get("titulo_original")) else ""),
             ("Género", ", ".join(o.get("generos") or [])),
             ("Dirección", ", ".join(o.get("directores") or [])),
             ("Reparto", ", ".join(o.get("actrices") or [])),
             ("Temporadas", o.get("temporadas")),
             ("Edad recomendada", f'{o["edad"]}+' if o.get("edad") else ""),
             ("Temáticas", ", ".join(o.get("tematicas") or []))]
    filas_html = "".join(f"<dt>{e(k)}</dt><dd>{e(v)}</dd>" for k, v in filas if v)
    # Dónde verla: no se enseñan las plataformas aquí, se manda a la ficha completa de la web
    donde = (f'<p class="donde"><a class="boton boton--claro" href="../../#/obra/{oid}">Ver en qué plataforma está</a></p>'
             if plataformas else "")
    rels = relacionadas(o, todas)
    rel_lista = ("<section class=\"rel\"><h2>Si te gusta, mira también</h2><ul>" + "".join(
        f'<li><a href="../{x["id"]}/">{e(x["titulo"])}</a> <span>{e(TIPO.get(x["tipo"], ""))}{" · " + str(x["anio"]) if x.get("anio") else ""}</span></li>'
        for x in rels) + "</ul></section>") if rels else ""
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
.boton--claro{{background:transparent;color:var(--violeta);border:2px solid var(--violeta);padding:10px 16px}}
.donde{{margin:0}}
.rel h2{{font:600 20px var(--serif);margin:0 0 8px}} .rel ul{{margin:0;padding-left:18px;display:grid;gap:4px}}
.rel a{{color:var(--violeta);font-weight:600}} .rel span{{color:var(--suave-t);font-size:14px}}
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
    {donde}
    {rel_lista}
  </div>
</main>
<footer>La Safoteca: catálogo gratuito de series y películas con representación lésbica y bisexual, con avisos de contenido.<br><a href="../../">Ir al catálogo</a> · <a href="../../obras/">Todas las series y películas</a></footer>
</body>
</html>
"""


# ---------- Colecciones: páginas que responden a búsquedas concretas ----------
def _avisos(o):
    return {(a["nombre"] if isinstance(a, dict) else a) for a in (o.get("avisos") or [])}


COLECCIONES = [
    {"slug": "series-lesbicas-final-feliz",
     "titulo": "Series lésbicas y bisexuales con final feliz",
     "intro": "Series en las que las protagonistas acaban juntas y con una relación sana. "
              "Ojo: esta lista te dice cómo acaban, así que contiene un pequeño destripe.",
     "filtro": lambda o: o["tipo"] == "serie" and o.get("final_feliz") is True},
    {"slug": "series-saficas-tailandesas",
     "titulo": "Series sáficas tailandesas (GL)",
     "intro": "Series tailandesas con protagonistas lesbianas o bisexuales, el llamado «Girls' Love» o GL.",
     "filtro": lambda o: o["tipo"] == "serie" and "Tailandia" in (o.get("pais") or "")},
    {"slug": "peliculas-lesbicas-donde-no-muere-la-lesbiana",
     "titulo": "Películas lésbicas donde no muere la lesbiana",
     "intro": "Películas sin el «síndrome de la lesbiana muerta» (ese cliché en el que el personaje lésbico o bisexual "
              "muere en la historia), según los avisos de contenido que hemos revisado.",
     # solo obras con avisos ya revisados (si no tiene ninguno, no sabemos si lo tendría)
     "filtro": lambda o: o["tipo"] == "pelicula" and (o.get("avisos") or o.get("final_feliz") is True)
                         and "Síndrome de la lesbiana muerta" not in _avisos(o)},
]


def coleccion(c, obras, noindex):
    sel = sorted((o for o in obras if c["filtro"](o)), key=lambda o: o["titulo"].casefold())
    items = "".join(
        f'<li><a href="../obra/{o["id"]}/">{e(o["titulo"])}</a>{" <span>(" + str(o["anio"]) + ")</span>" if o.get("anio") else ""}'
        f'{"<p>" + e(recorta(o.get("sinopsis"), 170)) + "</p>" if o.get("sinopsis") else ""}</li>' for o in sel)
    desc = recorta(f'{c["titulo"]}: {len(sel)} títulos en La Safoteca, el catálogo gratuito con avisos de contenido. {c["intro"]}')
    ld = {"@context": "https://schema.org", "@type": "ItemList", "name": c["titulo"], "numberOfItems": len(sel),
          "itemListElement": [{"@type": "ListItem", "position": i + 1, "url": f"{DOMINIO}/obra/{o['id']}/", "name": o["titulo"]}
                              for i, o in enumerate(sel)]}
    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(c["titulo"])} · La Safoteca</title>
<meta name="description" content="{e(desc)}">
{'<meta name="robots" content="noindex, nofollow">' if noindex else ''}
<link rel="canonical" href="{DOMINIO}/{c["slug"]}/">
<meta property="og:title" content="{e(c["titulo"])} · La Safoteca">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{DOMINIO}/{c["slug"]}/">
<meta property="og:image" content="{DOMINIO}/icons/icon-512.png">
<meta property="og:locale" content="es_ES">
<link rel="icon" href="../marca/buholira.svg" type="image/svg+xml">
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
{ESTILO_LISTA}
</head>
<body>
<header><a href="../"><img src="../marca/buholira.svg" alt="">La Safoteca</a></header>
<main>
<h1>{e(c["titulo"])}</h1>
<p>{e(c["intro"])} Hay {len(sel)} en La Safoteca; cada una tiene su ficha con nivel de relevancia, dónde verla y avisos de contenido ocultos hasta que decidas verlos.</p>
<p><a class="boton" href="../">Abrir el catálogo completo</a></p>
<ul class="tarjetas">{items}</ul>
<p><a href="../obras/">Todas las series y películas</a></p>
</main>
</body>
</html>
"""


ESTILO_LISTA = """<style>
:root{--violeta:#5d4a8a;--tinta:#2a2140;--suave-t:#5f5675;--papel:#fbf9fe;--sup:#fff;--linea:#ddd5ec;--btn:#5d4a8a;--btn-t:#fff;
  --serif:"Iowan Old Style","Palatino Linotype",Palatino,Georgia,serif;--sans:system-ui,-apple-system,"Segoe UI",Roboto,Arial,sans-serif}
@media (prefers-color-scheme:dark){:root{--violeta:#c4b6ea;--tinta:#efeaf8;--suave-t:#b9b0cf;--papel:#16131d;--sup:#201b2b;--linea:#3a3150;--btn:#b3a2dd;--btn-t:#1c1628}}
body{margin:0;background:var(--papel);color:var(--tinta);font:16px/1.55 var(--sans)}
header{padding:14px 16px;border-bottom:1px solid var(--linea);background:var(--sup)}
header a{display:inline-flex;align-items:center;gap:8px;color:var(--tinta);text-decoration:none;font:600 18px var(--serif)}
header img{width:30px;height:30px}
main{max-width:760px;margin:0 auto;padding:20px 16px 48px}
h1{font:600 clamp(26px,6vw,34px)/1.15 var(--serif);margin:0 0 8px} h2{font:600 22px var(--serif);margin:28px 0 8px}
a{color:var(--violeta)} li span{color:var(--suave-t);font-size:14px}
.boton{display:inline-block;background:var(--btn);color:var(--btn-t);text-decoration:none;font-weight:700;padding:12px 18px;border-radius:12px}
ul.columnas{padding-left:18px;columns:2 16rem;column-gap:24px} ul.columnas li{break-inside:avoid;margin:2px 0}
ul.tarjetas{list-style:none;padding:0;display:grid;gap:10px} ul.tarjetas li{background:var(--sup);border:1px solid var(--linea);border-radius:10px;padding:10px 14px}
ul.tarjetas a{font-weight:700} ul.tarjetas p{margin:4px 0 0;color:var(--suave-t);font-size:15px}
</style>"""


def indice(obras, noindex):
    """Página /obras/ con todas las series y películas enlazadas: así los buscadores llegan a todas las fichas."""
    def lista(tipo):
        sel = sorted((o for o in obras if o["tipo"] == tipo), key=lambda o: o["titulo"].casefold())
        return "".join(f'<li><a href="../obra/{o["id"]}/">{e(o["titulo"])}</a>{" <span>(" + str(o["anio"]) + ")</span>" if o.get("anio") else ""}</li>' for o in sel), len(sel)
    series, ns = lista("serie")
    pelis, np_ = lista("pelicula")
    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Todas las series y películas lésbicas y bisexuales · La Safoteca</title>
<meta name="description" content="Índice de las {ns} series y {np_} películas con representación lésbica y bisexual de La Safoteca, con avisos de contenido.">
{'<meta name="robots" content="noindex, nofollow">' if noindex else ''}
<link rel="canonical" href="{DOMINIO}/obras/">
<link rel="icon" href="../marca/buholira.svg" type="image/svg+xml">
<style>
:root{{--violeta:#5d4a8a;--tinta:#2a2140;--suave-t:#5f5675;--papel:#fbf9fe;--sup:#fff;--linea:#ddd5ec;
  --serif:"Iowan Old Style","Palatino Linotype",Palatino,Georgia,serif;--sans:system-ui,-apple-system,"Segoe UI",Roboto,Arial,sans-serif}}
@media (prefers-color-scheme:dark){{:root{{--violeta:#c4b6ea;--tinta:#efeaf8;--suave-t:#b9b0cf;--papel:#16131d;--sup:#201b2b;--linea:#3a3150}}}}
body{{margin:0;background:var(--papel);color:var(--tinta);font:16px/1.55 var(--sans)}}
header{{padding:14px 16px;border-bottom:1px solid var(--linea);background:var(--sup)}}
header a{{display:inline-flex;align-items:center;gap:8px;color:var(--tinta);text-decoration:none;font:600 18px var(--serif)}}
header img{{width:30px;height:30px}}
main{{max-width:760px;margin:0 auto;padding:20px 16px 48px}}
h1{{font:600 clamp(26px,6vw,34px)/1.15 var(--serif);margin:0 0 8px}} h2{{font:600 22px var(--serif);margin:28px 0 8px}}
ul{{padding-left:18px;columns:2 16rem;column-gap:24px}} li{{break-inside:avoid;margin:2px 0}}
a{{color:var(--violeta)}} li span{{color:var(--suave-t);font-size:14px}}
</style>
</head>
<body>
<header><a href="../"><img src="../marca/buholira.svg" alt="">La Safoteca</a></header>
<main>
<h1>Todas las series y películas</h1>
<p>Las {ns} series y {np_} películas con representación lésbica y bisexual de La Safoteca. Para buscar y filtrar por plataforma, temática o avisos, <a href="../">abre el catálogo</a>.</p>
<h2>Colecciones</h2><ul>{"".join(f'<li><a href="../{c["slug"]}/">{e(c["titulo"])}</a></li>' for c in COLECCIONES)}</ul>
<h2>Series ({ns})</h2><ul>{series}</ul>
<h2>Películas ({np_})</h2><ul>{pelis}</ul>
</main>
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
        (d / "index.html").write_text(pagina(o, nivel, a.noindex, datos["obras"]), encoding="utf-8")
    print(f"Páginas por obra: {len(datos['obras'])} en {web / 'obra'}")
    (web / "obras").mkdir(exist_ok=True)
    (web / "obras" / "index.html").write_text(indice(datos["obras"], a.noindex), encoding="utf-8")
    for c in COLECCIONES:
        (web / c["slug"]).mkdir(exist_ok=True)
        (web / c["slug"] / "index.html").write_text(coleccion(c, datos["obras"], a.noindex), encoding="utf-8")
        print(f"Colección /{c['slug']}/: {sum(1 for o in datos['obras'] if c['filtro'](o))} obras")
    print(f"Índice de obras: {web / 'obras' / 'index.html'}")
    if a.sitemap:
        sm = Path(a.sitemap)
        txt = sm.read_text(encoding="utf-8")
        filas = f"  <url><loc>{DOMINIO}/obras/</loc><lastmod>{datos['meta']['generado'][:10]}</lastmod></url>\n"
        filas += "".join(f"  <url><loc>{DOMINIO}/{c['slug']}/</loc><lastmod>{datos['meta']['generado'][:10]}</lastmod></url>\n" for c in COLECCIONES)
        filas += "".join(f"  <url><loc>{DOMINIO}/obra/{o['id']}/</loc><lastmod>{(o.get('publicada') or '')[:10] or datos['meta']['generado'][:10]}</lastmod></url>\n"
                        for o in datos["obras"])
        sm.write_text(txt.replace("</urlset>", filas + "</urlset>"), encoding="utf-8")
        print(f"Añadidas {len(datos['obras'])} direcciones a {sm}")


if __name__ == "__main__":
    main()
