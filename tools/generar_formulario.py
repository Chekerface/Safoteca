#!/usr/bin/env python3
"""Genera el script de Google (Apps Script) que crea el formulario de altas de La Safoteca.

Uso:  python3 tools/generar_formulario.py      ->  tools/formulario/crear_formulario.gs

Las listas de géneros, temáticas y avisos se leen de la base de datos (todos los valores del catálogo,
no los «pendientes de revisión»). Vuelve a ejecutarlo cuando el catálogo cambie y, si ya tienes el
formulario, pega el script nuevo y ejecuta `actualizarListas` (no hace falta crear otro formulario).
"""
import json, re, sqlite3, sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SALIDA = RAIZ / "tools" / "formulario" / "crear_formulario.gs"
MAX_POR_PREGUNTA = 100  # Google Forms va más fluido con listas cortas


def lista(db, tabla):
    return [r[0] for r in db.execute(f"SELECT nombre FROM {tabla} ORDER BY nombre COLLATE NOCASE")]


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
    db = sqlite3.connect(RAIZ / "safoteca.db")
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
