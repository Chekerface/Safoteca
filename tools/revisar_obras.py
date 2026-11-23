#!/usr/bin/env python3
"""Revisión rápida de las obras recién importadas: lo que conviene mirar a mano antes de mergear.

Avisa de: sinopsis que parece en inglés (o falta), obras sin póster descargado, películas sin dirección,
obras sin actrices, obras sin enlace de «dónde verla», y nombres de personas raros (otra escritura, paréntesis,
comillas, «as»/«como» + personaje, o casi iguales a una persona que ya existe).

Uso: python tools/revisar_obras.py --desde-id 497      # revisa las obras con id mayor que 497
Escribe el resultado en Markdown por pantalla (la acción «Importar formulario» lo pone en el resumen y en el PR).
"""
import argparse, re, sqlite3, sys, unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rutas import DB_DEFECTO, RAIZ  # noqa: E402

EN = set("the and of to a in is her his she he with for when who that their after but from an as by on this into".split())
ES = set("el la los las de del y en que su sus una un con por para cuando se es al lo como tras pero".split())


def idioma(t):
    pal = re.findall(r"[a-záéíóúñü']+", (t or "").lower())
    en, es = sum(p in EN for p in pal), sum(p in ES for p in pal)
    return "en" if en > es * 1.5 and en >= 3 else "es"


def clave(s):
    s = unicodedata.normalize("NFKD", s or "")
    return re.sub(r"[^a-z0-9]", "", "".join(c for c in s if not unicodedata.combining(c)).lower())


def raro(n):
    if any(ch.isalpha() and "LATIN" not in unicodedata.name(ch, "") for ch in n):
        return "otra escritura"
    if re.search(r"[()\[\]\"“”«»]|\d", n):
        return "paréntesis, comillas o números"
    if re.search(r"\s(as|como|es)\s", n, re.I):
        return "parece llevar el personaje"
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default=str(DB_DEFECTO))
    ap.add_argument("--desde-id", type=int, required=True)
    ap.add_argument("--web", default=str(RAIZ / "web"))
    a = ap.parse_args()
    db = sqlite3.connect(a.db)
    obras = db.execute("SELECT id, tipo, coalesce(titulo_es, titulo_original), sinopsis, estado FROM obra WHERE id > ? ORDER BY id",
                       (a.desde_id,)).fetchall()
    if not obras:
        print("No hay obras nuevas que revisar.")
        return
    claves = {}
    for pid, n in db.execute("SELECT id, nombre FROM persona"):
        claves.setdefault(clave(n), []).append((pid, n))
    puntos = []
    for oid, tipo, tit, sin, estado in obras:
        p = [] if estado == "publicada" else [f"queda como {estado} (no sale en la web)"]
        if not (sin or "").strip():
            p.append("sin sinopsis")
        elif idioma(sin) == "en":
            p.append("la sinopsis parece estar en inglés")
        if estado == "publicada" and not (Path(a.web) / "img" / f"{oid}_300.webp").exists():
            p.append("sin póster descargado")
        roles = dict(db.execute("SELECT rol, count(*) FROM obra_persona WHERE obra_id = ? GROUP BY rol", (oid,)).fetchall())
        if tipo == "pelicula" and not roles.get("director"):
            p.append("sin dirección")
        if not roles.get("actriz"):
            p.append("sin actrices")
        if not db.execute("SELECT 1 FROM obra_enlace WHERE obra_id = ? AND tipo = 'donde_ver'", (oid,)).fetchone():
            p.append("sin enlace de «dónde verla»")
        for pid, n in db.execute("SELECT p.id, p.nombre FROM obra_persona op JOIN persona p ON p.id = op.persona_id "
                                 "WHERE op.obra_id = ?", (oid,)):
            motivo = raro(n)
            if motivo:
                p.append(f"nombre raro «{n}» ({motivo})")
            casi = [m for q, m in claves.get(clave(n), []) if q != pid]
            if casi:
                p.append(f"«{n}» casi igual que «{casi[0]}», que ya existe")
        puntos.append((tit, oid, p))
    print(f"### Revisión de las {len(obras)} obras nuevas")
    for tit, oid, p in puntos:
        print(f"- **{tit}** (id {oid}): " + ("todo bien" if not p else "; ".join(p)))


if __name__ == "__main__":
    main()
