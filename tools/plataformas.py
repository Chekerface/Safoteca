"""Reconoce la plataforma y el país de un enlace de «dónde ver» leyendo la dirección.

Las reglas están en data/plataformas.csv (dominio, plataforma, país):
  * país con dos letras (ES, US, JP…): la web es siempre de ese país.
  * INT: sin país concreto (YouTube, o Prime Video en primevideo.com, que es la misma web en todos los países).
  * auto: el país va en la primera parte de la ruta (/es/, /us/, /es-es/…); si no hay, INT.
Lo que no coincide con ninguna regla se agrupa como «Otras» (webs no oficiales o plataformas por añadir).
Para añadir una plataforma basta con una línea nueva en el CSV; las más específicas van antes.
"""
import csv, re
from pathlib import Path
from urllib.parse import urlsplit

RAIZ = Path(__file__).resolve().parent.parent
OTRAS = "Otras"
_REGLAS = None


def reglas():
    global _REGLAS
    if _REGLAS is None:
        with open(RAIZ / "data" / "plataformas.csv", encoding="utf-8", newline="") as fh:
            _REGLAS = [(r["dominio"].lower(), r["plataforma"], r["pais"].strip()) for r in csv.DictReader(fh)]
    return _REGLAS


def reconocer(url):
    """Devuelve (plataforma, país). País es un código de 2 letras o 'INT'."""
    partes = urlsplit(url)
    host = (partes.hostname or "").lower().removeprefix("www.")
    for dom, nombre, pais in reglas():
        if host == dom or host.endswith("." + dom):
            if pais == "auto":
                seg = next((s for s in partes.path.split("/") if s), "").lower()
                m = re.fullmatch(r"[a-z]{2}(?:-([a-z]{2}))?", seg)
                pais = (m.group(1) or seg).upper() if m else "INT"
            return nombre, pais
    return OTRAS, "INT"
