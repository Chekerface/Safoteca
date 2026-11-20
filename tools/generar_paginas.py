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



# ---------- Temas de temporada (Navidad, Halloween) también en estas páginas ----------
# Usan los mismos config.js (fechas) y js/temas.js que la web, así que se activan los mismos días y con la misma
# vista previa (?tema=navidad / ?tema=normal en la dirección). Solo cambian el logotipo y la decoración.
def tema_head(pre):
    return f"""<script src="{pre}config.js"></script><script src="{pre}js/temas.js"></script>
<style>
.t-nav{{display:none}} [data-tema="navidad"] .t-nav{{display:block}} [data-tema="navidad"] .t-norm{{display:none}}
[data-tema="navidad"] body::before{{content:"";position:fixed;z-index:-1;pointer-events:none;top:0;left:0;right:0;height:400px;
  background:url("{pre}img/tema/copos.webp") 0 0/740px auto repeat-x;opacity:.85;
  filter:drop-shadow(0 0 1.2px rgb(156 136 187/.95)) drop-shadow(0 0 1px rgb(156 136 187/.6));
  -webkit-mask:linear-gradient(to bottom,#000 45%,transparent);mask:linear-gradient(to bottom,#000 45%,transparent)}}
@media (prefers-color-scheme:dark){{[data-tema="navidad"] body::before{{filter:none;opacity:.6}}}}
:root[data-tema="halloween"]{{--lila:#e8731f;--violeta:#a8400a;--btn:#a8400a;--linea:#f0cba5}}
@media (prefers-color-scheme:dark){{:root[data-tema="halloween"]{{--lila:#ff8a3d;--violeta:#ffa45c;--btn:#ff8a3d;--linea:#4d3057}}}}
[data-tema="halloween"] header,[data-tema="halloween"] .cab{{border-bottom:3px solid var(--lila)}}
</style>"""


def cabecera_simple(pre):
    """Cabecera de las páginas por obra y del índice: búho y nombre; en Navidad, el logotipo con gorro."""
    return (f'<header><a href="{pre}"><img class="t-norm" src="{pre}marca/buholira.svg" alt=""><span class="t-norm">La Safoteca</span>'
            f'<picture class="t-nav"><source media="(prefers-color-scheme: dark)" srcset="{pre}img/tema/logo-navidad-oscuro.webp">'
            f'<img src="{pre}img/tema/logo-navidad.webp" alt="La Safoteca" loading="lazy" style="width:auto;height:40px"></picture></a></header>')


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
{tema_head("../../")}
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
{cabecera_simple("../../")}
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


SLM = "Síndrome de la lesbiana muerta"

COLECCIONES = [
    {"slug": "series-lesbicas-final-feliz",
     "titulo": "Series lésbicas y bisexuales con final feliz",
     "titulo_html": "Series lésbicas y bisexuales con <em>final feliz</em>",
     "intro": "Series en las que las protagonistas acaban juntas y con una relación sana.",
     "nota": "Durante años, a nosotras nos tocaban los finales tristes. Aquí van las series en las que se quedan juntas, y bien.",
     "cifra": lambda todas, sel: (len(sel), f"de nuestras {sum(1 for o in todas if o['tipo'] == 'serie')} series acaban bien: juntas y con una relación sana."),
     "grafico": lambda todas: _grafico_final_feliz(todas),
     "titulo_dest": "Para un día de sofá y manta",
     "filtro": lambda o: o["tipo"] == "serie" and o.get("final_feliz") is True},
    {"slug": "series-saficas-tailandesas",
     "titulo": "Series sáficas tailandesas (GL)",
     "titulo_html": "Series sáficas <em>tailandesas</em> (GL)",
     "intro": "Series tailandesas con protagonistas lesbianas o bisexuales, el llamado «Girls' Love» o GL.",
     "nota": "Nos enganchamos al GL tailandés con GAP y ya no hubo vuelta atrás. Si nunca has visto uno, empieza por aquí.",
     "cifra": lambda todas, sel: (sum(1 for o in sel if o.get("relevancia") == "A" and o.get("final_feliz") is True),
                                  f"de {len(sel)} tienen a las protagonistas en el centro de la historia (nivel A) y acaban bien."),
     "grafico": lambda todas: _grafico_tailandesas(todas),
     "dato": lambda todas, sel: (f"{sum(1 for o in sel if any(p.get('n') == 'YouTube' for p in o.get('plataformas') or []))} se pueden ver gratis en YouTube."),
     "titulo_dest": "Para iniciarse",
     "destacadas": ["GAP THE SERIES", "Queendom", "Enemies with Benefits", "Heart Code", "Denied Love"],
     "filtro": lambda o: o["tipo"] == "serie" and "Tailandia" in (o.get("pais") or "")},
    {"slug": "peliculas-lesbicas-donde-no-muere-la-lesbiana",
     "titulo": "Películas lésbicas donde no muere la lesbiana",
     "titulo_html": "Películas lésbicas donde <em>no muere</em> la lesbiana",
     "intro": "Películas sin el «síndrome de la lesbiana muerta», ese cliché en el que el personaje lésbico o bisexual "
              "muere en la historia. Sin destripes: solo te decimos que ella llega viva a los créditos.",
     "nota": "Empezamos La Safoteca porque estábamos hartas de encariñarnos con un personaje para verlo morir. "
             "Esta es la lista que nos habría gustado tener.",
     "cifra": lambda todas, sel: (len(sel), f"de nuestras {sum(1 for o in todas if o['tipo'] == 'pelicula')} películas no caen en el "
                                            f"síndrome de la lesbiana muerta. Solo {sum(1 for o in todas if o['tipo'] == 'pelicula' and SLM in _avisos(o))} sí."),
     "barra": lambda todas: (sum(1 for o in todas if o["tipo"] == "pelicula" and SLM not in _avisos(o)),
                             sum(1 for o in todas if o["tipo"] == "pelicula" and SLM in _avisos(o)), "viva", "muere"),
     "grafico_anios": True,
     # sin el aviso (una película sin ningún aviso está revisada: no tiene nada que avisar)
     "filtro": lambda o: o["tipo"] == "pelicula" and SLM not in _avisos(o)},
]


def _grafico_anios(todas):
    """SVG sin JavaScript: películas del catálogo por año y cuántas tienen el síndrome."""
    pel = [o for o in todas if o["tipo"] == "pelicula" and o.get("anio") and o["anio"] >= 1985]
    a0, a1 = 1985, max(o["anio"] for o in pel)
    tot = [sum(1 for o in pel if o["anio"] == y) for y in range(a0, a1 + 1)]
    slm = [sum(1 for o in pel if o["anio"] == y and SLM in _avisos(o)) for y in range(a0, a1 + 1)]
    W, H, iz, ab = 340, 150, 22, 20
    top = max(tot) or 1
    x = lambda i: iz + i * (W - iz - 6) / (len(tot) - 1)
    y = lambda v: 8 + (H - ab - 8) * (1 - v / top)
    linea = lambda serie: " ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(serie))
    area = f"{x(0):.1f},{y(0):.1f} " + linea(tot) + f" {x(len(tot) - 1):.1f},{y(0):.1f}"
    marcas = "".join(f'<text x="{x(a - a0):.1f}" y="{H - 4}" text-anchor="middle">{a}</text>' for a in (1990, 2000, 2010, 2020) if a <= a1)
    ejes = "".join(f'<line x1="{iz}" x2="{W - 6}" y1="{y(v):.1f}" y2="{y(v):.1f}" class="g"/><text x="{iz - 5}" y="{y(v) + 4:.1f}" text-anchor="end">{v}</text>'
                   for v in range(0, top + 1, 5))
    puntos = "".join(f'<circle cx="{x(i):.1f}" cy="{y(v):.1f}" r="2.6" class="m"/>' for i, v in enumerate(slm) if v)
    return f"""<figure class="anios"><svg viewBox="0 0 {W} {H}" role="img" aria-label="Películas del catálogo por año de estreno desde {a0}: el total sube hasta {top}; las que tienen el síndrome de la lesbiana muerta son como mucho {max(slm)} al año.">
{ejes}<polygon points="{area}" class="a"/><polyline points="{linea(tot)}" class="t"/><polyline points="{linea(slm)}" class="s"/>{puntos}{marcas}</svg>
<figcaption><span class="ley t"></span>películas del catálogo por año <span class="ley s"></span>con el síndrome de la lesbiana muerta</figcaption></figure>"""


def _barras(filas, aria, unidad=""):
    """Barras horizontales en SVG sin JavaScript. filas = [(etiqueta, valor, texto_valor)]."""
    W, alto, iz = 340, 26, 86
    top = max(v for _, v, _ in filas) or 1
    H = alto * len(filas) + 4
    cuerpo = ""
    for n, (et, v, txt) in enumerate(filas):
        y = n * alto + 4
        ancho = max(2, (W - iz - 44) * v / top)
        cuerpo += (f'<text x="{iz - 8}" y="{y + 15}" text-anchor="end">{et}</text>'
                   f'<rect x="{iz}" y="{y + 3}" width="{ancho:.1f}" height="16" rx="3" class="t-b"/>'
                   f'<text x="{iz + ancho + 6:.1f}" y="{y + 15}" class="v">{txt}</text>')
    return f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="{e(aria)}">{cuerpo}</svg>'


def _grafico_final_feliz(todas):
    series = [o for o in todas if o["tipo"] == "serie" and o.get("anio")]
    tramos = [(1990, 2009, "hasta 2009"), (2010, 2014, "2010–2014"), (2015, 2019, "2015–2019"), (2020, 2022, "2020–2022"), (2023, 2100, "2023–hoy")]
    filas = []
    for a, b, et in tramos:
        g = [o for o in series if a <= o["anio"] <= b]
        if g:
            pct = round(100 * sum(1 for o in g if o.get("final_feliz") is True) / len(g))
            filas.append((et, pct, f"{pct} %"))
    svg = _barras(filas, "Porcentaje de series del catálogo con final feliz según su año de estreno: " +
                  ", ".join(f"{et} {t}" for et, _, t in filas))
    return f'<figure class="anios">{svg}<figcaption>series del catálogo con final feliz, según cuándo se estrenaron</figcaption></figure>'


def _grafico_tailandesas(todas):
    th = [o for o in todas if o["tipo"] == "serie" and "Tailandia" in (o.get("pais") or "") and o.get("anio")]
    if not th:
        return ""
    años = range(min(o["anio"] for o in th), max(o["anio"] for o in th) + 1)
    filas = [(str(a), n, str(n)) for a in años for n in [sum(1 for o in th if o["anio"] == a)]]
    svg = _barras(filas, "Series tailandesas del catálogo por año de estreno: " + ", ".join(f"{a}: {n}" for a, _, n in filas))
    return f'<figure class="anios">{svg}<figcaption>series tailandesas del catálogo por año de estreno</figcaption></figure>'


def _poster(o, ancho=300):
    return f'../img/{o["poster"]}_{ancho}.webp' if o.get("poster") else ""


def coleccion(c, obras, noindex):
    # Las tarjetas abren la ficha de la web (#/obra/ID). Los buscadores siguen llegando a las páginas por obra
    # por el sitemap, el índice /obras/ y los datos estructurados de esta página.
    sel = sorted((o for o in obras if c["filtro"](o)), key=lambda o: o["titulo"].casefold())
    REL = {"A": 3, "B": 2, "C": 1}
    if c.get("destacadas"):
        por_titulo = {k: o for o in sel for k in (o["titulo"], o.get("titulo_original"))}
        destacadas = [por_titulo[t] for t in c["destacadas"] if t in por_titulo and por_titulo[t].get("poster")]
    else:
        destacadas = sorted((o for o in sel if o.get("poster")),
                            key=lambda o: (-REL.get(o.get("relevancia"), 0), o.get("final_feliz") is not True, -(o.get("anio") or 0)))[:3]
    marca_ff = c["slug"] != "series-lesbicas-final-feliz"
    etiqueta = lambda o: '<span class="ff">final feliz</span>' if marca_ff and o.get("final_feliz") is True else ""
    # Pocos clics: el póster y el botón abren la ficha de la web (#/obra/ID); el título enlaza la página por obra,
    # que es la que ven los buscadores (Google no sigue lo que va tras «#»).
    app = lambda o: f'../#/obra/{o["id"]}'
    estatica = lambda o: f'../obra/{o["id"]}/'
    dest_html = "".join(
        f'<div class="dest"><a class="pos" href="{app(o)}" aria-label="Abrir {e(o["titulo"])} en La Safoteca">'
        f'<img src="{_poster(o)}" alt="" loading="lazy" width="300" height="450">{etiqueta(o)}</a>'
        f'<a class="dt" href="{estatica(o)}">{e(o["titulo"])}</a></div>' for o in destacadas)
    def tarjeta(o):
        img = (f'<img src="{_poster(o)}" alt="" loading="lazy" width="300" height="450">' if o.get("poster")
               else '<span class="sinpos"></span>')
        anio = f' <i>{o["anio"]}</i>' if o.get("anio") else ""
        sin = f'<small>{e(recorta(o.get("sinopsis"), 140))}</small>' if o.get("sinopsis") else ""
        return (f'<li><a class="lp" href="{app(o)}" aria-label="Abrir {e(o["titulo"])} en La Safoteca">{img}</a>'
                f'<div><a class="lt" href="{estatica(o)}"><b>{e(o["titulo"])}</b></a>{anio}{sin}'
                f'<a class="abrir" href="{app(o)}">Dónde verla y avisos <span aria-hidden="true">→</span></a></div></li>')
    items = "".join(tarjeta(o) for o in sel)
    nota = (f'<blockquote class="nota"><p>«{e(c["nota"])}»</p><cite>— el equipo de La Safoteca</cite></blockquote>'
            if c.get("nota") else "")
    cifra = ""
    if c.get("cifra"):
        n, frase = c["cifra"](obras, sel)
        cifra = f'<div class="cifra"><span class="num">{n}</span><span>{e(frase)}</span></div>'
    barra = ""
    if c.get("barra"):
        bien, mal, et_b, et_m = c["barra"](obras)
        tot = bien + mal or 1
        barra = (f'<div class="barra" role="img" aria-label="{bien} {et_b}, {mal} {et_m}"><span class="b" style="width:{100 * bien / tot:.1f}%"></span>'
                 f'<span class="m" style="width:{100 * mal / tot:.1f}%"></span></div><p class="ley-b">lila: {et_b} · negro: {et_m}</p>')
    grafico = _grafico_anios(obras) if c.get("grafico_anios") else (c["grafico"](obras) if c.get("grafico") else "")
    dato = f'<p class="dato">{e(c["dato"](obras, sel))}</p>' if c.get("dato") else ""
    desc = recorta(f'{c["titulo"]}: {len(sel)} títulos en La Safoteca, el catálogo gratuito con avisos de contenido. {c["intro"]}')
    ld = {"@context": "https://schema.org", "@type": "ItemList", "name": c["titulo"], "numberOfItems": len(sel),
          "itemListElement": [{"@type": "ListItem", "position": i + 1, "url": f"{DOMINIO}/obra/{o['id']}/", "name": o["titulo"]}
                              for i, o in enumerate(sel)]}
    resto = len(sel) - len(destacadas)
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
<meta name="theme-color" content="#1d1726">
<link rel="icon" href="../marca/buholira.svg" type="image/svg+xml">
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
{ESTILO_COLECCION}
{tema_head("../")}
</head>
<body>
<header class="cab">
  {cabecera_fragmentos()}
  <h1>{c["titulo_html"]}</h1>
  <p>{e(c["intro"])}</p>
</header>
<main>
{nota}
{cifra}
{barra}
{grafico}
{dato}
{'<h2>' + e(c.get("titulo_dest", "Para empezar esta noche")) + '</h2><div class="dests">' + dest_html + '</div>' if destacadas else ''}
{'<p class="mas">… y ' + str(resto) + ' más, de la A a la Z ↓</p>' if resto > 0 else ''}
<ul class="lista">{items}</ul>
<p class="todas"><a href="../obras/">Todas las series y películas</a></p>
</main>
<div class="cta"><div><b>Ábrelas en el catálogo</b><small>filtra por plataforma y esconde lo que no quieras ver</small></div>
<a href="../#/catalogo">Abrir <span aria-hidden="true">→</span></a></div>
</body>
</html>
"""


ESTILO_COLECCION = """<style>
:root{--lila:#9c88bb;--negro:#1d1726;--tinta:#1d1726;--suave:#5f5675;--papel:#fbf9fe;--sup:#fff;--linea:#ddd5ec;--claro:#c9bbe0;
  --serif:"Iowan Old Style","Palatino Linotype",Palatino,Georgia,serif;--sans:system-ui,-apple-system,"Segoe UI",Roboto,Arial,sans-serif;
  --mono:"Roboto Mono",ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
@media (prefers-color-scheme:dark){:root{--tinta:#efeaf8;--suave:#b9b0cf;--papel:#16131d;--sup:#201b2b;--linea:#3a3150;--negro:#0e0b13}}
*{box-sizing:border-box} body{margin:0;background:var(--papel);color:var(--tinta);font:16px/1.55 var(--sans)}
.cab{background:var(--negro);color:#f3eef9;padding:18px 18px 34px}
.cab .marca{display:inline-flex;align-items:flex-end;gap:10px;color:var(--claro);text-decoration:none;font:13px var(--mono)}
.cab .marca img{height:44px;width:auto} .cab .marca span{padding-bottom:4px;border-left:1px solid #4a3f5c;padding-left:10px}
.cab-top{display:flex;align-items:center;justify-content:space-between;gap:12px}
.sel{display:flex;gap:16px;font:14px var(--sans)} .sel a{color:#8f84a3;text-decoration:none;padding:6px 0}
.sel a[aria-current]{color:#f3eef9}
.cols{display:grid;gap:22px;margin:26px 0 0}
.col{display:block;color:inherit;text-decoration:none;background:var(--sup);border:1px solid var(--linea);border-radius:10px;padding:16px 16px 14px}
.col h2{font:400 24px/1.15 var(--serif);margin:0 0 14px} .col h2 em{color:var(--lila)}
.col .nota{margin:0 0 12px;transform:rotate(-.6deg)} .col .n{font:13px var(--mono);color:var(--suave)}
.mas a{color:var(--suave)}
.cab h1{font:400 clamp(30px,8vw,46px)/1.05 var(--serif);margin:18px 0 0;max-width:760px}
.cab h1 em{color:var(--lila)} .cab p{color:var(--claro);margin:12px 0 0;max-width:640px}
main{max-width:760px;margin:0 auto;padding:0 16px 120px}
.nota{margin:-18px 0 0;background:#fff;color:#1d1726;border:1.5px solid #1d1726;border-radius:4px;padding:14px 16px 12px;transform:rotate(-1deg)}
.nota p{margin:0;font:italic 17px/1.5 var(--serif)} .nota cite{display:block;margin-top:8px;font:12px var(--mono);color:#5f5675;font-style:normal}
.cifra{display:flex;align-items:baseline;gap:12px;margin:26px 0 0} .cifra .num{font:400 60px/1 var(--serif)} .cifra span:last-child{color:var(--suave)}
.barra{display:flex;gap:2px;height:14px;margin:12px 0 0;border-radius:3px;overflow:hidden}
.barra .b{background:var(--lila)} .barra .m{background:#1d1726} @media (prefers-color-scheme:dark){.barra .m{background:#efeaf8}}
.ley-b{font:11px var(--mono);color:var(--suave);margin:6px 0 0}
.anios{margin:22px 0 0} .anios svg{width:100%;height:auto;font:10px var(--mono);fill:var(--suave)}
.anios .g{stroke:var(--linea)} .anios .a{fill:var(--lila);opacity:.14;stroke:none} .anios .t{fill:none;stroke:var(--lila);stroke-width:2}
.anios .s{fill:none;stroke:var(--tinta);stroke-width:1.6;stroke-dasharray:4 3} .anios .m{fill:var(--tinta)}
.anios figcaption{font:11px var(--mono);color:var(--suave);display:flex;flex-wrap:wrap;gap:4px 10px;align-items:center}
.anios .t-b{fill:var(--lila)} .anios .v{fill:var(--tinta)}
.dato{margin:18px 0 0;padding:10px 12px;border-left:3px solid var(--lila);background:var(--sup);font:15px var(--serif)}
.ley{display:inline-block;width:14px;height:0;border-top:2px solid var(--lila)} .ley.s{border-top:2px dashed var(--tinta)}
h2{font:400 22px var(--serif);margin:30px 0 12px}
.dests{display:grid;grid-template-columns:repeat(3,1fr);gap:10px} .dest{color:var(--tinta);text-decoration:none;font-size:13px}
.pos{position:relative;display:block;aspect-ratio:2/3;border-radius:4px;overflow:hidden;background:var(--linea)}
.pos img{width:100%;height:100%;object-fit:cover;display:block}
.ff{position:absolute;left:5px;bottom:5px;background:#1d1726;color:#fff;font-size:10px;padding:2px 6px;border-radius:2px}
.dt{display:block;margin-top:5px;line-height:1.3}
.mas{color:var(--suave);font-size:14px;margin:16px 0 8px}
.lista{list-style:none;padding:0;margin:0;display:grid;gap:8px}
.lista li{display:flex;gap:12px;align-items:flex-start;background:var(--sup);border:1px solid var(--linea);border-radius:8px;padding:8px}
.lista .lp{flex:none} .lista img,.sinpos{display:block;width:52px;height:78px;object-fit:cover;border-radius:3px;background:var(--linea)}
.lista .lt{color:var(--tinta);text-decoration:none} .lista b{font:600 16px var(--serif)} .lista i{font-style:normal;color:var(--suave);font-size:13px;margin-left:4px}
.lista small{display:block;color:var(--suave);font-size:13.5px;line-height:1.45;margin-top:3px}
.abrir{display:inline-block;margin-top:6px;font-size:13px;font-weight:600;color:#1d1726;background:var(--lila);text-decoration:none;padding:4px 10px;border-radius:999px}
.dest .dt{color:var(--tinta);text-decoration:none}
.todas{margin:22px 0 0} .todas a{color:var(--tinta)}
.cta{position:sticky;bottom:0;display:flex;align-items:center;gap:12px;background:var(--lila);color:#1d1726;padding:12px max(16px,calc(50vw - 364px))}
.cta div{flex:1} .cta b{display:block;font:400 17px var(--serif)} .cta small{display:block;font-size:12.5px;color:#2b2433}
.cta a{background:#1d1726;color:#fff;text-decoration:none;padding:11px 16px;border-radius:999px;white-space:nowrap;font-weight:600}
@media (min-width:640px){.dests{grid-template-columns:repeat(3,minmax(0,170px))}}
</style>"""


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



def cabecera_fragmentos():
    """Logotipo (lleva al catálogo) y el selector «Catálogo · Fragmentos» de la parte de arriba (F1, F2)."""
    return ('<div class="cab-top"><a class="marca" href="../"><img class="t-norm" src="../marca/logo-horizontal-oscuro.svg" '
            'alt="La Safoteca" width="86" height="44"><img class="t-nav" src="../img/tema/logo-navidad-oscuro.webp" alt="La Safoteca" '
            'height="44" loading="lazy"></a><nav class="sel" aria-label="Secciones"><a href="../">Catálogo</a>'
            '<a href="../fragmentos/" aria-current="page">Fragmentos</a></nav></div>')


def portada_fragmentos(obras, noindex):
    """F1 · Página de entrada de Fragmentos: qué es y una tarjeta por colección (título y cita del equipo)."""
    tarjetas = []
    for c in COLECCIONES:
        sel = [o for o in obras if c["filtro"](o)]
        ns = sum(1 for o in sel if o["tipo"] == "serie")
        que = (f"{ns} series" if ns == len(sel) else f"{len(sel)} películas" if ns == 0 else f"{len(sel)} obras")
        tarjetas.append(f'''<a class="col" href="../{c["slug"]}/"><h2>{c["titulo_html"]}</h2>
<div class="nota"><p>«{e(c["nota"])}»</p><cite>— el equipo de La Safoteca</cite></div>
<span class="n">{que} →</span></a>''')
    desc = ("Fragmentos de La Safoteca: opiniones, recomendaciones y noticias del equipo sobre series y películas "
            "lésbicas y bisexuales.")
    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Fragmentos · La Safoteca</title>
<meta name="description" content="{e(desc)}">
{'<meta name="robots" content="noindex, nofollow">' if noindex else ''}
<link rel="canonical" href="{DOMINIO}/fragmentos/">
<meta property="og:title" content="Fragmentos · La Safoteca">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{DOMINIO}/fragmentos/">
<meta property="og:image" content="{DOMINIO}/icons/icon-512.png">
<meta property="og:locale" content="es_ES">
<meta name="theme-color" content="#1d1726">
<link rel="icon" href="../marca/buholira.svg" type="image/svg+xml">
{ESTILO_COLECCION}
{tema_head("../")}
</head>
<body>
<header class="cab">
  {cabecera_fragmentos()}
  <h1>Fragmentos</h1>
  <p>Aquí iremos dejando nuestras opiniones, recomendaciones y noticias. Es nuestra forma de que nos conozcáis un poco más.</p>
</header>
<main>
<div class="cols">
{"".join(tarjetas)}
</div>
<p class="mas"><a href="../obras/">Todas las series y películas</a> · <a href="../">Ir al catálogo</a></p>
</main>
</body>
</html>
"""


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
{tema_head("../")}
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
{cabecera_simple("../")}
<main>
<h1>Todas las series y películas</h1>
<p>Las {ns} series y {np_} películas con representación lésbica y bisexual de La Safoteca. Para buscar y filtrar por plataforma, temática o avisos, <a href="../">abre el catálogo</a>.</p>
<h2><a href="../fragmentos/">Fragmentos</a>: colecciones del equipo</h2><ul>{"".join(f'<li><a href="../{c["slug"]}/">{e(c["titulo"])}</a></li>' for c in COLECCIONES)}</ul>
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
    (web / "fragmentos").mkdir(exist_ok=True)
    (web / "fragmentos" / "index.html").write_text(portada_fragmentos(datos["obras"], a.noindex), encoding="utf-8")
    print(f"Portada de Fragmentos: {web / 'fragmentos' / 'index.html'}")
    print(f"Índice de obras: {web / 'obras' / 'index.html'}")
    if a.sitemap:
        sm = Path(a.sitemap)
        txt = sm.read_text(encoding="utf-8")
        filas = f"  <url><loc>{DOMINIO}/obras/</loc><lastmod>{datos['meta']['generado'][:10]}</lastmod></url>\n"
        filas += f"  <url><loc>{DOMINIO}/fragmentos/</loc><lastmod>{datos['meta']['generado'][:10]}</lastmod></url>\n"
        filas += "".join(f"  <url><loc>{DOMINIO}/{c['slug']}/</loc><lastmod>{datos['meta']['generado'][:10]}</lastmod></url>\n" for c in COLECCIONES)
        filas += "".join(f"  <url><loc>{DOMINIO}/obra/{o['id']}/</loc><lastmod>{(o.get('publicada') or '')[:10] or datos['meta']['generado'][:10]}</lastmod></url>\n"
                        for o in datos["obras"])
        sm.write_text(txt.replace("</urlset>", filas + "</urlset>"), encoding="utf-8")
        print(f"Añadidas {len(datos['obras'])} direcciones a {sm}")


if __name__ == "__main__":
    main()
