#!/usr/bin/env python3
"""Genera el script de Google (Apps Script) que crea el formulario de altas de La Safoteca.

Uso:  python3 tools/generar_formulario.py      ->  tools/formulario/crear_formulario.gs

Las listas de géneros, temáticas y avisos son las ACEPTADAS: data/mapeos/generos_aceptados.csv,
tematicas_aceptadas.csv y avisos_aceptados.csv (las mismas que vigilan los importadores). Una etiqueta
que exista en la base de datos pero no esté en esas listas no se ofrece en el formulario. Vuelve a ejecutarlo cuando el catálogo cambie y, si ya tienes el
formulario, pega el script nuevo y ejecuta `actualizarListas` (no hace falta crear otro formulario).
"""
import csv, json, re, sqlite3, sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from rutas import DB_DEFECTO, COPIAS, PRIVADO  # noqa: E402,F401

SALIDA = RAIZ / "tools" / "formulario" / "crear_formulario.gs"
MAX_POR_PREGUNTA = 100  # Google Forms va más fluido con listas cortas


ACEPTADAS = {"genero": "generos_aceptados.csv", "tematica": "tematicas_aceptadas.csv", "aviso": "avisos_aceptados.csv"}


def lista(db, tabla):
    """Etiquetas aceptadas, ordenadas sin distinguir mayúsculas. Avisa si alguna no existe en la base de datos."""
    with open(RAIZ / "data" / "mapeos" / ACEPTADAS[tabla], encoding="utf-8-sig", newline="") as fh:
        nombres = [r["nombre"].strip() for r in csv.DictReader(fh) if r["nombre"].strip()]
    en_bd = {r[0] for r in db.execute(f"SELECT nombre FROM {tabla}")}
    for n in nombres:
        if n not in en_bd:
            print(f"AVISO: «{n}» está en la lista aceptada de {tabla} pero no en la base de datos")
    return sorted(nombres, key=str.casefold)


def trozos(valores, base):
    """Parte una lista larga en preguntas «Temática (parte 1 de 4)»…"""
    n = -(-len(valores) // MAX_POR_PREGUNTA)
    tam = -(-len(valores) // n)
    out = []
    for i in range(n):
        parte = valores[i * tam:(i + 1) * tam]
        titulo = f"{base} (parte {i + 1} de {n})" if n > 1 else base
        out.append({"titulo": titulo, "rango": f"de «{parte[0]}» a «{parte[-1]}»" if n > 1 else "", "opciones": parte})
    return out


def relevancia():
    txt = (RAIZ / "web" / "config.js").read_text(encoding="utf-8")
    return {k: re.search(rf'{k}:\s*"([^"]+)"', txt).group(1) for k in "ABC"}


def main():
    db = sqlite3.connect(DB_DEFECTO)
    datos = {
        "generos": trozos(lista(db, "genero"), "Género"),
        "tematicas": trozos(lista(db, "tematica"), "Temática"),
        "avisos": trozos(lista(db, "aviso"), "Aviso"),
        "relevancia": relevancia(),
    }
    plantilla = (RAIZ / "tools" / "formulario" / "plantilla.gs.txt").read_text(encoding="utf-8")
    SALIDA.write_text(plantilla.replace("__DATOS__", json.dumps(datos, ensure_ascii=False, indent=1)), encoding="utf-8")
    print(f"Escrito {SALIDA.relative_to(RAIZ)}: {sum(len(g['opciones']) for g in datos['generos'])} géneros, "
          f"{sum(len(g['opciones']) for g in datos['tematicas'])} temáticas, "
          f"{sum(len(g['opciones']) for g in datos['avisos'])} avisos")


if __name__ == "__main__":
    sys.exit(main())
