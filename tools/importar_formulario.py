#!/usr/bin/env python3
"""Carga en la base de datos las respuestas del formulario de altas de La Safoteca.

Uso:
    python tools/importar_formulario.py respuestas.xlsx --simular     # solo informa, no guarda
    python tools/importar_formulario.py respuestas.xlsx               # guarda y regenera la web
    python tools/importar_formulario.py respuestas.csv --publicar     # además publica las obras completas

El archivo es el que se descarga de la hoja de respuestas del formulario (Archivo → Descargar → .xlsx o .csv).
Cada fila es una obra, así que se pueden cargar muchas de golpe. Se lee la primera hoja, por nombre de columna
(la columna «Marca temporal» y el orden no importan). El formulario se crea con tools/formulario/crear_formulario.gs.

Diferencias con importar_plantilla.py:
  * Solo AÑADE obras nuevas: nunca actualiza ni toca las que ya existen.
  * Validación de repetidos: una fila no se importa si la obra ya está en la base de datos o si aparece antes
    en el propio archivo. Se compara tipo + título original (o título en España), sin tener en cuenta
    mayúsculas, tildes ni signos («NCIS: Hawai'i» = «NCIS Hawaii»), y el año si las dos filas lo tienen.
    También se omite si su enlace de Letterboxd ya lo tiene otra obra. Si un enlace de «dónde verla» o el
    póster ya lo usa otra obra, se avisa (pero se importa).
  * Las obras entran como «borrador». Con --publicar pasan a publicadas si tienen sinopsis y nivel de relevancia.
  * El correo con el que se rellenó el formulario queda como «revisore».
Antes de guardar se hace una copia de la base de datos en data/privado/copias/.
Las incidencias salen por pantalla y en informes/incidencias_formulario.csv.
"""
import csv, re, sys, unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import importar_plantilla as ip  # noqa: E402
from importar_excel import RAIZ, limpio, a_entero  # noqa: E402

URL_RE = re.compile(r"https?://[^\s,;<>\"']+")


def clave(s):
    """Texto comparable: sin tildes, mayúsculas ni signos."""
    s = unicodedata.normalize("NFKD", str(s or ""))
    return re.sub(r"[^a-z0-9]", "", "".join(c for c in s if not unicodedata.combining(c)).lower())


def url_clave(u):
    return re.sub(r"^https?://(www\.)?", "", u.strip().lower()).rstrip("/")


def anio_de(v):
    m = re.match(r"\s*(\d{4})", str(v or ""))
    return int(m.group(1)) if m else None


class Formulario(ip.Plantilla):
    def __init__(self, db, informes, args):
        super().__init__(db, informes)
        self.args = args
        # obras que ya existen: (id, tipo, {claves de título}, año)
        self.conocidas = []
        for oid, tipo, tit_o, tit_es, anio in db.execute("SELECT id, tipo, titulo_original, titulo_es, anio FROM obra"):
            self.conocidas.append((f"id {oid} de la base de datos", tipo, {clave(tit_o), clave(tit_es)} - {""}, anio))
        self.lb_usados = {}
        ruta = RAIZ / "data" / "letterboxd.csv"
        if ruta.exists():
            with open(ruta, encoding="utf-8", newline="") as fh:
                for r in csv.DictReader(fh):
                    self.lb_usados[url_clave(r["url"])] = f"id {r['id']} de la base de datos"
        self.urls_usadas = {}
        for oid, url in db.execute("SELECT obra_id, url FROM obra_enlace WHERE tipo='donde_ver'"):
            self.urls_usadas[url_clave(url)] = f"id {oid}"
        for oid, url in db.execute("SELECT id, poster_origen FROM obra WHERE poster_origen IS NOT NULL"):
            self.urls_usadas.setdefault(url_clave(url), f"id {oid} (póster)")

    def fila(self, n, f):
        f = dict(f)
        f.pop("id", None)                       # el formulario nunca actualiza obras existentes
        if self.args.publicar:
            f["revisada"] = "Sí"
        tit_o = limpio(f.get("titulo original"))
        tit_es = limpio(f.get("titulo en espana"))
        titulo = tit_o or tit_es
        if not titulo:
            return
        tipo = ip.TIPOS.get((limpio(f.get("tipo")) or "").lower())
        anio = anio_de(f.get("ano"))
        claves = {clave(tit_o), clave(tit_es)} - {""}
        if tipo:
            for donde, t, ks, a in self.conocidas:
                if t == tipo and ks & claves and (anio is None or a is None or a == anio):
                    self.inc(n, titulo, "Título original", tit_o or tit_es,
                             f"repetida: ya existe ({donde}). No se importa")
                    self.res["omitidas"].append(titulo)
                    return
        lb = limpio(f.get("letterboxd (enlace)")) or limpio(f.get("letterboxd"))
        if lb and url_clave(lb) in self.lb_usados:
            self.inc(n, titulo, "Letterboxd", lb, f"repetido: ese enlace ya lo tiene otra obra ({self.lb_usados[url_clave(lb)]}). No se importa")
            self.res["omitidas"].append(titulo)
            return
        for campo in ("donde verla (enlace)", "donde verla (enlace 2)", "poster (enlace de la imagen)"):
            for u in URL_RE.findall(limpio(f.get(campo)) or ""):
                if url_clave(u) in self.urls_usadas:
                    self.inc(n, titulo, campo, u, f"aviso: este enlace ya lo usa otra obra ({self.urls_usadas[url_clave(u)]}); se importa, revisa que no sea la misma obra")
        antes = len(self.res["nuevas"])
        super().fila(n, f)
        if len(self.res["nuevas"]) > antes:     # entró: ya cuenta para detectar repetidos dentro del propio archivo
            oid = self.res["nuevas"][-1][0]
            self.conocidas.append((f"la fila {n} de este mismo archivo", tipo, claves, anio))
            if lb:
                self.lb_usados[url_clave(lb)] = f"la fila {n} de este mismo archivo"
            for campo in ("donde verla (enlace)", "donde verla (enlace 2)", "poster (enlace de la imagen)"):
                for u in URL_RE.findall(limpio(f.get(campo)) or ""):
                    self.urls_usadas.setdefault(url_clave(u), f"la fila {n} de este mismo archivo")


def argumentos(ap):
    ap.add_argument("--publicar", action="store_true",
                    help="publica las obras que tengan sinopsis y nivel de relevancia (por defecto entran como borrador)")


if __name__ == "__main__":
    ip.main(Formulario, __doc__, "incidencias_formulario.csv", argumentos)
