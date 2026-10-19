#!/usr/bin/env python3
"""Pasa la temática «Final Feliz» al campo «final_feliz» de cada obra y borra la temática.

Motivo: la temática se veía en la ficha sin ocultar (destripaba el final). El campo final_feliz se enseña
dentro de los avisos de contenido, que están ocultos por defecto, y tiene su propio filtro.

Uso:  python tools/migrar_final_feliz.py --simular   |   python tools/migrar_final_feliz.py
Es seguro repetirlo. Las obras que ya tenían final_feliz = 0 (final no feliz) no se tocan.
"""
import argparse, shutil, sqlite3
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--db", default=str(RAIZ / "safoteca.db"))
ap.add_argument("--simular", action="store_true")
a = ap.parse_args()
db = sqlite3.connect(a.db)
t = db.execute("SELECT id FROM tematica WHERE nombre = 'Final Feliz'").fetchone()
if not t:
    print("La temática «Final Feliz» ya no existe: nada que hacer.")
    raise SystemExit
if not a.simular:
    copia = RAIZ / "data" / "privado" / "copias" / f"safoteca_antes_final_feliz_{datetime.now():%Y%m%d_%H%M%S}.db"
    copia.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(a.db, copia)
    print("Copia de seguridad:", copia.relative_to(RAIZ))
filas = db.execute("""SELECT o.id, COALESCE(o.titulo_es, o.titulo_original), o.final_feliz FROM obra o
                      JOIN obra_tematica x ON x.obra_id = o.id WHERE x.tematica_id = ?""", (t[0],)).fetchall()
nuevas = [f for f in filas if f[2] is None]
choques = [f for f in filas if f[2] == 0]
print(f"{len(filas)} obras con la temática; {len(nuevas)} pasan a final_feliz = sí; "
      f"{len(filas) - len(nuevas) - len(choques)} ya lo tenían; {len(choques)} tienen final_feliz = no (se respeta).")
for f in choques:
    print("  OJO, contradicción:", f[1])
if not a.simular:
    for f in nuevas:
        db.execute("UPDATE obra SET final_feliz = 1 WHERE id = ?", (f[0],))
    db.execute("DELETE FROM obra_tematica WHERE tematica_id = ?", (t[0],))
    db.execute("DELETE FROM tematica WHERE id = ?", (t[0],))
    db.commit()
    print("Hecho. Ejecuta tools/exportar_json.py y tools/generar_formulario.py")
else:
    print("(Simulación: no se ha guardado nada.)")
