#!/usr/bin/env python3
"""Colecciones de Fragmentos (F2) desde un Excel, sin tocar Python.

Las colecciones viven en web/data/colecciones.json. Este archivo se edita con un Excel
(fragmentos/colecciones.xlsx): una fila por colección. La acción «Publicar colecciones» lo convierte,
lo comprueba y lo publica en PRE (o abre el PR a PRO).

Uso:
    python tools/colecciones.py --a-excel  fragmentos/colecciones.xlsx   # JSON actual → Excel (para editarlo)
    python tools/colecciones.py --de-excel fragmentos/colecciones.xlsx   # Excel → web/data/colecciones.json
    python tools/colecciones.py --comprobar                              # solo comprueba el JSON actual

Huecos que se rellenan solos en «Cifra: número», «Cifra: frase» y «Dato» (entre llaves):
    {total}                 obras de la colección
    {en_espana}             de la colección, las que se pueden ver en España
    {nivel_a}               de la colección, las de nivel A
    {final_feliz}           de la colección, las que tienen final feliz
    {nivel_a_final_feliz}   de la colección, nivel A y con final feliz
    {gratis_youtube}        de la colección, las que están gratis en YouTube
    {antes_de_2010}         de la colección, estrenadas antes de ese año (vale cualquier año)
    {desde_2020}            de la colección, estrenadas ese año o después (vale cualquier año)
    {peliculas} {series}    del catálogo entero
    {peliculas_muere}       películas del catálogo con el aviso «Síndrome de la lesbiana muerta»
    {peliculas_no_muere}    películas del catálogo sin ese aviso
"""
import argparse, json, re, sys, unicodedata
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
JSON = RAIZ / "web" / "data" / "colecciones.json"
SLM = "Síndrome de la lesbiana muerta"
GRAFICOS = {"Ninguno": "", "Plataformas": "plataformas", "Final feliz en series": "final_feliz_series",
            "Tailandesas por año": "tailandesas", "Lesbiana muerta (barra y años)": "lesbiana_muerta"}
TIPOS = {"Películas": "pelicula", "Series": "serie", "Series y películas": ""}

# (cabecera del Excel, clave del JSON, ayuda)
COLUMNAS = [
    ("Orden", "orden", "Posición en la portada de Fragmentos (1 = la primera)."),
    ("Activa", "activa", "Sí = se publica. No = se guarda pero no sale."),
    ("Título", "titulo", "Pon entre *asteriscos* la parte que va en lila y cursiva. Ej.: Películas lésbicas de *Navidad*"),
    ("Dirección web", "slug", "Opcional. Lo que va tras lasafoteca.com/. Si lo dejas vacío se hace con el título. "
                              "No la cambies en una colección ya publicada: se romperían los enlaces."),
    ("Antetítulo", "antetitulo", "Opcional. Línea pequeña sobre el título. Ej.: Especial Navidad"),
    ("Introducción", "intro", "Una o dos frases bajo el título (también es la descripción para Google)."),
    ("Nota del equipo", "nota", "Opcional. La cita en tarjeta blanca, firmada por el equipo."),
    ("Tipo", "tipo", "Películas, Series o Series y películas."),
    ("Temáticas", "tematicas", "Opcional. Separadas por «;». Entra la obra que tenga ALGUNA."),
    ("Géneros", "generos", "Opcional. Separados por «;». Entra la obra que tenga ALGUNO."),
    ("Plataforma en España", "plataforma", "Opcional. Una: Netflix, Filmin, Prime Video, HBO Max…"),
    ("País", "pais", "Opcional. Ej.: Tailandia"),
    ("Niveles", "niveles", "Opcional. A, B o C separados por «;». Vacío = todos."),
    ("Final feliz", "final_feliz", "Opcional. Sí = solo con final feliz. Vacío = da igual."),
    ("Sin el aviso", "sin_aviso", "Opcional. Quita las obras con este aviso. Ej.: Síndrome de la lesbiana muerta"),
    ("Año desde", "desde", "Opcional."),
    ("Año hasta", "hasta", "Opcional."),
    ("Cifra: número", "cifra_numero", "Opcional. El número grande. Normalmente {total}. Ver la lista de huecos."),
    ("Cifra: frase", "cifra_frase", "Lo que va junto al número. Puede llevar huecos: de nuestras {peliculas} películas…"),
    ("Gráfico", "grafico", "Ninguno, Plataformas, Final feliz en series, Tailandesas por año o Lesbiana muerta (barra y años)."),
    ("Dato", "dato", "Opcional. El recuadro con borde lila. Puede llevar huecos: Solo {en_espana} se pueden ver en España."),
    ("¿Echas en falta?", "proponer", "Sí = añade «¿Echas en falta alguna serie o película? Añádela →»."),
    ("Título de las recomendadas", "titulo_dest", "Opcional. Por defecto: Para empezar esta noche"),
    ("Recomendadas", "destacadas", "Opcional. Títulos separados por «;», tal como salen en la web. Vacío = las 3 mejores solas."),
    ("Nota de las recomendadas", "nota_dest", "Opcional. Texto en cursiva bajo los pósters."),
    ("Botón del catálogo", "catalogo", "Opcional. Normalmente vacío: se hace solo con Tipo, Temáticas, Géneros, Niveles, "
                                       "Final feliz y Plataforma. Solo para casos raros: ?tipo=serie&tem=Navidad"),
]
LISTAS = {"tematicas", "generos", "niveles", "destacadas"}
SI_NO = {"activa", "final_feliz", "proponer"}


def sin_tildes(s):
    return "".join(c for c in unicodedata.normalize("NFKD", s or "") if not unicodedata.combining(c)).lower()


def slug(texto):
    return re.sub(r"[^a-z0-9]+", "-", sin_tildes(texto.replace("*", ""))).strip("-")


def si(v):
    return sin_tildes(str(v or "")).strip() in ("si", "s", "x", "1", "true", "verdadero")


# ---------- Lo que hace falta para calcular y comprobar ----------

def avisos(o):
    return {(a["nombre"] if isinstance(a, dict) else a) for a in (o.get("avisos") or [])}


def plataforma_es(o, nombre):
    return any(sin_tildes(p.get("n")) == sin_tildes(nombre) and p.get("p") in ("ES", "INT") for p in o.get("plataformas") or [])


def filtro(c):
    """Función que dice si una obra entra en la colección."""
    def entra(o):
        if c.get("tipo") and o["tipo"] != c["tipo"]:
            return False
        if c.get("tematicas") and not set(c["tematicas"]) & set(o.get("tematicas") or []):
            return False
        if c.get("generos") and not set(c["generos"]) & set(o.get("generos") or []):
            return False
        if c.get("plataforma") and not plataforma_es(o, c["plataforma"]):
            return False
        if c.get("pais") and sin_tildes(c["pais"]) not in sin_tildes(o.get("pais")):
            return False
        if c.get("niveles") and o.get("relevancia") not in c["niveles"]:
            return False
        if c.get("final_feliz") and o.get("final_feliz") is not True:
            return False
        if c.get("sin_aviso") and c["sin_aviso"] in avisos(o):
            return False
        if c.get("desde") and (o.get("anio") or 0) < int(c["desde"]):
            return False
        if c.get("hasta") and (o.get("anio") or 9999) > int(c["hasta"]):
            return False
        return True
    return entra


def huecos(todas, sel):
    pelis = [o for o in todas if o["tipo"] == "pelicula"]
    h = {"total": len(sel),
         "en_espana": sum(1 for o in sel if o.get("disponible_espana")),
         "nivel_a": sum(1 for o in sel if o.get("relevancia") == "A"),
         "final_feliz": sum(1 for o in sel if o.get("final_feliz") is True),
         "nivel_a_final_feliz": sum(1 for o in sel if o.get("relevancia") == "A" and o.get("final_feliz") is True),
         "gratis_youtube": sum(1 for o in sel if any(p.get("n") == "YouTube" for p in o.get("plataformas") or [])),
         "peliculas": len(pelis), "series": sum(1 for o in todas if o["tipo"] == "serie"),
         "peliculas_muere": sum(1 for o in pelis if SLM in avisos(o)),
         "peliculas_no_muere": sum(1 for o in pelis if SLM not in avisos(o))}
    return h


def rellenar(texto, todas, sel):
    """Cambia {hueco} por su número. Lanza KeyError con el nombre si un hueco no existe."""
    h = huecos(todas, sel)
    def uno(m):
        k = m.group(1)
        if k in h:
            return str(h[k])
        a = re.fullmatch(r"antes_de_(\d{4})", k)
        if a:
            return str(sum(1 for o in sel if (o.get("anio") or 9999) < int(a.group(1))))
        d = re.fullmatch(r"desde_(\d{4})", k)
        if d:
            return str(sum(1 for o in sel if (o.get("anio") or 0) >= int(d.group(1))))
        raise KeyError(k)
    return re.sub(r"\{([a-z0-9_]+)\}", uno, texto or "")


def catalogo(c):
    """Enlace del botón «Abrir» al catálogo de la web, ya filtrado como la colección (si se puede)."""
    if c.get("catalogo"):
        return c["catalogo"]
    from urllib.parse import quote
    p = []
    if c.get("tipo"):
        p.append(f"tipo={c['tipo']}")
    for clave, campo in (("gen", "generos"), ("tem", "tematicas"), ("rel", "niveles")):
        if c.get(campo):
            p.append(f"{clave}={quote('|'.join(c[campo]))}")
    if c.get("final_feliz"):
        p.append("final=si")
    if c.get("plataforma"):
        p.append(f"plat={quote(c['plataforma'])}")
    return "?" + "&".join(p) if p else ""


# ---------- Excel ↔ JSON ----------

def leer_json(ruta=JSON):
    return json.loads(Path(ruta).read_text(encoding="utf-8"))["colecciones"] if Path(ruta).exists() else []


def a_excel(colecciones, ruta):
    from openpyxl import Workbook
    from openpyxl.comments import Comment
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.worksheet.datavalidation import DataValidation
    wb = Workbook()
    ws = wb.active
    ws.title = "Colecciones"
    ws.append([c[0] for c in COLUMNAS])
    lila = PatternFill("solid", fgColor="9C88BB")
    for i, (cab, _, ayuda) in enumerate(COLUMNAS, 1):
        celda = ws.cell(1, i)
        celda.font, celda.fill = Font(name="Arial", bold=True, color="FFFFFF"), lila
        celda.alignment = Alignment(wrap_text=True, vertical="top")
        celda.comment = Comment(ayuda, "La Safoteca")
        ws.column_dimensions[celda.column_letter].width = 14 if len(cab) < 12 else 24
    for clave in ("titulo", "intro", "nota", "cifra_frase", "dato", "nota_dest", "destacadas"):
        i = [c[1] for c in COLUMNAS].index(clave) + 1
        ws.column_dimensions[ws.cell(1, i).column_letter].width = 48
    inv_tipos = {v: k for k, v in TIPOS.items()}
    inv_graf = {v: k for k, v in GRAFICOS.items()}
    for c in sorted(colecciones, key=lambda c: c.get("orden", 99)):
        fila = []
        for _, k, _ in COLUMNAS:
            v = c.get(k)
            if k in LISTAS:
                v = "; ".join(v or [])
            elif k in SI_NO:
                v = "Sí" if v else ("No" if k == "activa" else "")
            elif k == "tipo":
                v = inv_tipos.get(v or "", "Series y películas")
            elif k == "grafico":
                v = inv_graf.get(v or "", "Ninguno")
            fila.append(v)
        ws.append(fila)
    for fila in ws.iter_rows(min_row=2):
        for celda in fila:
            celda.font = Font(name="Arial")
            celda.alignment = Alignment(wrap_text=True, vertical="top")
    ws.freeze_panes = "C2"
    col = {k: ws.cell(1, i + 1).column_letter for i, (_, k, _) in enumerate(COLUMNAS)}
    for k, opciones in (("activa", "Sí,No"), ("final_feliz", "Sí"), ("proponer", "Sí"),
                        ("tipo", ",".join(TIPOS)), ("grafico", ",".join(GRAFICOS))):
        dv = DataValidation(type="list", formula1=f'"{opciones}"', allow_blank=True)
        ws.add_data_validation(dv)
        dv.add(f"{col[k]}2:{col[k]}200")
    ay = wb.create_sheet("Ayuda")
    ay.append(["Columna", "Qué poner"])
    for cab, _, ayuda in COLUMNAS:
        ay.append([cab, ayuda])
    ay.append([])
    ay.append(["Huecos", "Se escriben entre llaves y se cambian por el número al publicar:"])
    for linea in __doc__.split("entre llaves):")[1].strip().splitlines():
        hueco, _, que = linea.strip().partition(" ")
        ay.append([hueco, que.strip()])
    ay.append([])
    ay.append(["Cómo publicar", "1) Guarda este Excel como fragmentos/colecciones.xlsx en la rama main de GitHub "
               "(Add file → Upload files). 2) Actions → «Publicar colecciones» → Run workflow: «PRE» para verlo en "
               "lasafoteca.com/uat/, «PRO» para abrir el PR a la web."])
    for fila in ay.iter_rows():
        for celda in fila:
            celda.font = Font(name="Arial", bold=celda.column == 1)
            celda.alignment = Alignment(wrap_text=True, vertical="top")
    ay.column_dimensions["A"].width, ay.column_dimensions["B"].width = 28, 100
    wb.save(ruta)


def de_excel(ruta):
    """Lee el Excel y devuelve (colecciones, errores). Los errores llevan fila y columna."""
    from openpyxl import load_workbook
    ws = load_workbook(ruta, data_only=True)["Colecciones"]
    cab = [str(c.value or "").strip() for c in ws[1]]
    falta = [c[0] for c in COLUMNAS if c[0] not in cab]
    if falta:
        return [], [f"Faltan columnas en el Excel: {', '.join(falta)}"]
    errores, out = [], []
    for n, fila in enumerate(ws.iter_rows(min_row=2, values_only=True), 2):
        crudo = dict(zip(cab, fila))
        if not any(v not in (None, "") for v in crudo.values()):
            continue
        c = {}
        for cabecera, k, _ in COLUMNAS:
            v = crudo.get(cabecera)
            v = v.strip() if isinstance(v, str) else v
            if k in LISTAS:
                c[k] = [x.strip() for x in str(v or "").replace("\n", ";").split(";") if x.strip()]
            elif k in SI_NO:
                c[k] = si(v)
            elif k == "tipo":
                c[k] = TIPOS.get(v or "Series y películas")
                if c[k] is None:
                    errores.append(f"Fila {n}, «Tipo»: «{v}» no vale; usa {', '.join(TIPOS)}.")
            elif k == "grafico":
                c[k] = GRAFICOS.get(v or "Ninguno")
                if c[k] is None:
                    errores.append(f"Fila {n}, «Gráfico»: «{v}» no vale; usa {', '.join(GRAFICOS)}.")
            elif k in ("orden", "desde", "hasta"):
                try:
                    c[k] = int(v) if v not in (None, "") else None
                except (TypeError, ValueError):
                    errores.append(f"Fila {n}, «{cabecera}»: tiene que ser un número.")
            else:
                c[k] = "" if v is None else str(v)
        c["fila"] = n
        if crudo.get("Activa") in (None, ""):
            c["activa"] = True
        out.append({k: v for k, v in c.items() if v not in (None, "", [], False) or k in ("activa",)})
    return out, errores


# ---------- Comprobaciones ----------

def comprobar(colecciones, obras, cats):
    errores, avisos_ = [], []
    vistos = set()
    tem = set(cats.get("tematicas", []))
    gen = set(cats.get("generos", []))
    avs = {a["nombre"] if isinstance(a, dict) else a for a in cats.get("avisos", [])}
    plats = {p.get("n") for o in obras for p in o.get("plataformas") or []}
    for c in colecciones:
        donde = f"Fila {c['fila']}" if c.get("fila") else f"«{c.get('titulo', '?')}»"
        if not c.get("titulo"):
            errores.append(f"{donde}: falta el título.")
            continue
        if not c.get("intro"):
            errores.append(f"{donde}: falta la introducción.")
        c.setdefault("slug", slug(c["titulo"]))
        if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", c["slug"]):
            errores.append(f"{donde}: la dirección web «{c['slug']}» solo puede llevar minúsculas sin tildes, números y guiones.")
        if c["slug"] in vistos:
            errores.append(f"{donde}: la dirección web «{c['slug']}» está repetida.")
        if c["slug"] in ("obra", "obras", "fragmentos", "quienes-somos", "uat", "data", "img", "css", "js", "equipo", "marca", "icons"):
            errores.append(f"{donde}: la dirección web «{c['slug']}» está reservada.")
        vistos.add(c["slug"])
        for campo, validas, nombre in (("tematicas", tem, "temática"), ("generos", gen, "género")):
            for x in c.get(campo, []):
                if x not in validas:
                    import difflib
                    cerca = difflib.get_close_matches(sin_tildes(x), {sin_tildes(v): v for v in validas}, n=1, cutoff=0.7)
                    pista = f" ¿Quizá «{ {sin_tildes(v): v for v in validas}[cerca[0]] }»?" if cerca else ""
                    errores.append(f"{donde}: la {nombre} «{x}» no existe en el catálogo.{pista}")
        if c.get("sin_aviso") and c["sin_aviso"] not in avs:
            errores.append(f"{donde}: el aviso «{c['sin_aviso']}» no existe en el catálogo.")
        if c.get("plataforma") and not any(sin_tildes(c["plataforma"]) == sin_tildes(p) for p in plats):
            errores.append(f"{donde}: la plataforma «{c['plataforma']}» no está en el catálogo.")
        for x in c.get("niveles", []):
            if x not in ("A", "B", "C"):
                errores.append(f"{donde}: el nivel «{x}» no vale; usa A, B o C.")
        if c.get("grafico") == "plataformas" and not c.get("plataforma"):
            errores.append(f"{donde}: el gráfico «Plataformas» necesita una «Plataforma en España».")
        if not c.get("activa"):
            continue
        sel = [o for o in obras if filtro(c)(o)]
        if not sel:
            errores.append(f"{donde}: no entra ninguna obra con estos filtros.")
            continue
        for campo, nombre in (("cifra_numero", "Cifra: número"), ("cifra_frase", "Cifra: frase"), ("dato", "Dato")):
            try:
                v = rellenar(c.get(campo), obras, sel)
                if campo == "cifra_numero" and v and not v.strip().isdigit():
                    errores.append(f"{donde}: «Cifra: número» tiene que acabar siendo un número (sale «{v}»).")
            except KeyError as k:
                errores.append(f"{donde}, «{nombre}»: el hueco {{{k.args[0]}}} no existe. Mira la hoja «Ayuda».")
        if c.get("cifra_frase") and not c.get("cifra_numero"):
            c["cifra_numero"] = "{total}"
        por_titulo = {}
        for o in sel:
            for t in (o["titulo"], o.get("titulo_original")):
                if t:
                    por_titulo.setdefault(sin_tildes(t), o)
        todos = {sin_tildes(t): o for o in obras for t in (o["titulo"], o.get("titulo_original")) if t}
        for t in c.get("destacadas", []):
            o = por_titulo.get(sin_tildes(t))
            if not o:
                errores.append(f"{donde}: la recomendada «{t}» " + ("no cumple los filtros de la colección."
                                                                    if sin_tildes(t) in todos else "no está en el catálogo."))
            elif not o.get("poster"):
                avisos_.append(f"{donde}: «{t}» no tiene póster; no saldrá entre las recomendadas.")
        c["n_obras"] = len(sel)
    return errores, avisos_


def escribir_json(colecciones, ruta=JSON):
    limpias = []
    for c in sorted(colecciones, key=lambda c: (c.get("orden") or 99, c["titulo"])):
        limpias.append({k: v for k, v in c.items() if k not in ("fila", "n_obras")})
    Path(ruta).write_text(json.dumps({"colecciones": limpias}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--a-excel", metavar="XLSX")
    g.add_argument("--de-excel", metavar="XLSX")
    g.add_argument("--comprobar", action="store_true")
    ap.add_argument("--web", default=str(RAIZ / "web"), help="carpeta web (para leer obras.json y catalogos.json)")
    ap.add_argument("--salida", default=None, help="dónde escribir el JSON (por defecto web/data/colecciones.json)")
    a = ap.parse_args()
    web = Path(a.web)
    if a.a_excel:
        a_excel(leer_json(web / "data" / "colecciones.json"), a.a_excel)
        print(f"Excel escrito en {a.a_excel}")
        return
    obras = json.loads((web / "data" / "obras.json").read_text(encoding="utf-8"))["obras"]
    cats = json.loads((web / "data" / "catalogos.json").read_text(encoding="utf-8"))
    if a.de_excel:
        cols, errores = de_excel(a.de_excel)
    else:
        cols, errores = leer_json(web / "data" / "colecciones.json"), []
    e2, avisos_ = comprobar(cols, obras, cats) if not errores else ([], [])
    errores += e2
    for x in avisos_:
        print(f"AVISO: {x}")
    if errores:
        print("NO SE PUBLICA. Corrige esto en el Excel y vuelve a lanzarla:")
        for x in errores:
            print(f"  - {x}")
        sys.exit(1)
    for c in sorted(cols, key=lambda c: c.get("orden") or 99):
        estado = f"{c.get('n_obras', 0)} obras" if c.get("activa") else "no activa (no se publica)"
        print(f"  {c.get('orden') or '-'}. {c['titulo'].replace('*', '')} → /{c['slug']}/ · {estado}")
    if a.de_excel:
        escribir_json(cols, a.salida or web / "data" / "colecciones.json")
        print(f"{len(cols)} colecciones guardadas en {a.salida or web / 'data' / 'colecciones.json'}")


if __name__ == "__main__":
    main()
