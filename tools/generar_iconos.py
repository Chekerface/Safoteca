"""Genera los iconos PNG de la app a partir del búholira (web/marca/buholira-blanco.svg).
Según el manual de marca, para icono de app se usa solo el búholira, sin deformarlo ni mezclar colores:
aquí va en blanco sobre el lila de marca #9C88BB.
Uso: python tools/generar_iconos.py   (necesita playwright + chromium)"""
from pathlib import Path
from playwright.sync_api import sync_playwright

RAIZ = Path(__file__).resolve().parent.parent
WEB = RAIZ / "web"
LILA = "#9C88BB"
svg = (WEB / "marca" / "buholira-blanco.svg").read_text(encoding="utf-8")

# (archivo, tamaño, ancho del búho como fracción del lienzo)
ICONOS = [("icon-192.png", 192, .70), ("icon-512.png", 512, .70),
          ("icon-maskable-512.png", 512, .56),      # zona segura de los iconos "maskable"
          ("apple-touch-icon.png", 180, .70)]

def html(tam, frac):
    ancho = round(tam * frac)
    return f"""<html><body style="margin:0;width:{tam}px;height:{tam}px;background:{LILA};display:grid;place-items:center">
<div style="width:{ancho}px">{svg.replace('<svg ', '<svg style="width:100%;height:auto;display:block" ', 1)}</div></body></html>"""

with sync_playwright() as p:
    nav = p.chromium.launch()
    for nombre, tam, frac in ICONOS:
        pag = nav.new_page(viewport={"width": tam, "height": tam})
        pag.set_content(html(tam, frac))
        pag.screenshot(path=str(WEB / "icons" / nombre))
        pag.close()
    nav.close()
print("Iconos generados en", WEB / "icons")
