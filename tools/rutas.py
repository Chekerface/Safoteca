"""Dónde están los datos privados de La Safoteca.

La base de datos (safoteca.db), sus copias de seguridad y los archivos privados (p. ej. revisoras.csv) NO viven
en este repositorio público, sino en el repositorio PRIVADO Chekerface/Safoteca-datos, clonado al lado de este:

    .../Safoteca          (este repositorio, público)
    .../Safoteca-datos    (privado: safoteca.db, copias/, privado/)

También se puede indicar con la variable de entorno SAFOTECA_DATOS. Si no se encuentra, se usa safoteca.db en la
raíz de este repositorio (como antes) y se avisa, porque esa copia NO está guardada en ningún sitio.
Después de cambiar la base de datos hay que subirla al repositorio privado (commit + push).
"""
import os, sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def _carpeta_datos():
    env = os.environ.get("SAFOTECA_DATOS")
    candidatas = [Path(env)] if env else [RAIZ.parent / "Safoteca-datos", RAIZ.parent / "safoteca-datos"]
    for c in candidatas:
        if (c / "safoteca.db").exists() or (c / ".git").exists():
            return c.resolve()
    return None


DATOS = _carpeta_datos()
if DATOS:
    DB_DEFECTO = DATOS / "safoteca.db"
    COPIAS = DATOS / "copias"
    PRIVADO = DATOS / "privado"
else:
    DB_DEFECTO = RAIZ / "safoteca.db"
    COPIAS = RAIZ / "data" / "privado" / "copias"
    PRIVADO = RAIZ / "data" / "privado"
    print("AVISO: no encuentro el repositorio privado Safoteca-datos al lado de este; uso safoteca.db de la raíz, "
          "que no se guarda en ningún sitio. Clona Chekerface/Safoteca-datos junto a este repositorio.", file=sys.stderr)
