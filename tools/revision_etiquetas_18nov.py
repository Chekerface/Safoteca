#!/usr/bin/env python3
"""Octava tanda de etiquetas: decisiones del Excel de revisión de Carmen (18 de noviembre de 2026).

Géneros que desaparecen (sus obras pasan al género general y, si se indica, reciben una temática):
    Aventura → Acción + temática «Aventura»            Comedia dramática → Comedia + temática «Comedia dramática»
    Comedia negra → Comedia + temática «Humor negro»   Sitcom → Comedia + temática «Sitcom»
    Suspense → Thriller + temática «Suspense»          Ficción sobrenatural → Fantasía + temática «Ficción sobrenatural»
    Fantástico → Fantasía                              Horror → Terror
Temáticas:
    «Aventuras» pasa a llamarse «Aventura».
    «Romcom» (nueva) para todas las obras con el género Comedia romántica.
    «Pareja» se une a «Relación de pareja»; de ella cuelgan Pareja idiota, Pareja sana y Relaciones complicadas.
    Dejan de ser temáticas (sus obras reciben el aviso del mismo nombre): Consumo de alcohol, Consumo de drogas,
    Discriminación fuerte, Pareja tóxica y Pseudoincesto. Alcoholismo y Drogodependencia siguen siendo temáticas,
    pero sueltas (solo cuelgan de Consumo de alcohol/drogas en los avisos).
    «Adorabilidad absoluta» se elimina (temática y aviso).
Las reglas para lo que llegue después (formulario, Excel) están en data/mapeos.

Uso:
    python tools/revision_etiquetas_18nov.py --simular   # solo informa
    python tools/revision_etiquetas_18nov.py             # guarda (hace antes una copia de la base de datos)
Después: python tools/exportar_json.py y python tools/generar_formulario.py
Es seguro repetirlo.
"""
import argparse, shutil, sqlite3, sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rutas import DB_DEFECTO, COPIAS  # noqa: E402

GENEROS = [  # (género que desaparece, género al que pasa, temática que reciben sus obras o None)
    ("Aventura", "Acción", "Aventura"),
    ("Comedia dramática", "Comedia", "Comedia dramática"),
    ("Comedia negra", "Comedia", "Humor negro"),
    ("Sitcom", "Comedia", "Sitcom"),
    ("Suspense", "Thriller", "Suspense"),
    ("Ficción sobrenatural", "Fantasía", "Ficción sobrenatural"),
    ("Fantástico", "Fantasía", None),
    ("Horror", "Terror", None),
]
A_AVISO = ["Consumo de alcohol", "Consumo de drogas", "Discriminación fuerte", "Pareja tóxica", "Pseudoincesto"]
ELIMINAR = "Adorabilidad absoluta"
# (hija, grupo anterior o None, grupo nuevo o None) en las temáticas
GRUPOS = [("Pareja idiota", None, "Relación de pareja"), ("Pareja sana", None, "Relación de pareja"),
          ("Relaciones complicadas", "Relaciones", "Relación de pareja"),
          ("Alcoholismo", "Consumo de alcohol", None), ("Drogodependencia", "Consumo de drogas", None)]


def ident(db, tabla, nombre, crear=False):
    r = db.execute(f"SELECT id FROM {tabla} WHERE nombre = ? COLLATE NOCASE", (nombre,)).fetchone()
    if r:
        db.execute(f"UPDATE {tabla} SET nombre = ? WHERE id = ?", (nombre, r[0]))  # ortografía buena
        return r[0]
    if not crear:
        return None
    return db.execute(f"INSERT INTO {tabla}(nombre, pendiente_revision) VALUES (?, 0)", (nombre,)).lastrowid


def obras(db, enlace, col, i):
    return [r[0] for r in db.execute(f"SELECT obra_id FROM {enlace} WHERE {col} = ?", (i,))]


def poner(db, enlace, col, i, lista):
    return sum(db.execute(f"INSERT OR IGNORE INTO {enlace}(obra_id, {col}) VALUES (?, ?)", (o, i)).rowcount for o in lista)


def aplicar(db, inf):
    # Antes que nada, el nuevo nombre de «Aventuras»
    if ident(db, "tematica", "Aventuras") and not db.execute("SELECT 1 FROM tematica WHERE nombre = 'Aventura'").fetchone():
        db.execute("UPDATE tematica SET nombre = 'Aventura' WHERE nombre = 'Aventuras'")
        inf.append("temática: «Aventuras» pasa a llamarse «Aventura»")
    for viejo, nuevo, tem in GENEROS:
        g = ident(db, "genero", viejo)
        if g is None:
            continue
        lista = obras(db, "obra_genero", "genero_id", g)
        n1 = poner(db, "obra_genero", "genero_id", ident(db, "genero", nuevo, True), lista)
        extra = ""
        if tem:
            n2 = poner(db, "obra_tematica", "tematica_id", ident(db, "tematica", tem, True), lista)
            extra = f"; temática «{tem}» a {n2}"
        db.execute("DELETE FROM obra_genero WHERE genero_id = ?", (g,))
        db.execute("DELETE FROM genero WHERE id = ?", (g,))
        inf.append(f"género: «{viejo}» desaparece ({len(lista)} obras) → «{nuevo}» nuevo en {n1}{extra}")
    # Romcom para las comedias románticas
    cr = ident(db, "genero", "Comedia romántica")
    if cr:
        n = poner(db, "obra_tematica", "tematica_id", ident(db, "tematica", "Romcom", True), obras(db, "obra_genero", "genero_id", cr))
        inf.append(f"temática: «Romcom» a {n} obras con Comedia romántica")
    # Pareja → Relación de pareja
    p, rp = ident(db, "tematica", "Pareja"), ident(db, "tematica", "Relación de pareja", True)
    if p:
        n = poner(db, "obra_tematica", "tematica_id", rp, obras(db, "obra_tematica", "tematica_id", p))
        db.execute("DELETE FROM obra_tematica WHERE tematica_id = ?", (p,))
        db.execute("DELETE FROM tematica WHERE id = ?", (p,))  # sus grupos se borran solos
        inf.append(f"temática: «Pareja» unida a «Relación de pareja» ({n} obras nuevas)")
    # Temáticas que solo son avisos
    for nombre in A_AVISO:
        t = ident(db, "tematica", nombre)
        if t is None:
            continue
        lista = obras(db, "obra_tematica", "tematica_id", t)
        a = ident(db, "aviso", nombre)
        n = poner(db, "obra_aviso", "aviso_id", a, lista) if a else 0
        db.execute("DELETE FROM obra_tematica WHERE tematica_id = ?", (t,))
        db.execute("DELETE FROM tematica WHERE id = ?", (t,))
        inf.append(f"temática: «{nombre}» deja de ser temática ({len(lista)} obras; {n} reciben ahora el aviso)")
    # Adorabilidad absoluta, fuera
    for tabla in ("tematica", "aviso"):
        i = ident(db, tabla, ELIMINAR)
        if i:
            n = db.execute(f"DELETE FROM obra_{tabla} WHERE {tabla}_id = ?", (i,)).rowcount
            db.execute(f"DELETE FROM {tabla} WHERE id = ?", (i,))
            inf.append(f"{'temática' if tabla == 'tematica' else 'aviso'}: «{ELIMINAR}» eliminada ({n} obras)")
    # Grupos de temáticas
    for hija, antes, despues in GRUPOS:
        h = ident(db, "tematica", hija)
        if h is None:
            continue
        if antes and (a := ident(db, "tematica", antes)):
            if db.execute("DELETE FROM tematica_grupo WHERE hijo_id = ? AND padre_id = ?", (h, a)).rowcount:
                inf.append(f"temática: «{hija}» ya no cuelga de «{antes}»")
        if despues:
            d = ident(db, "tematica", despues)
            if db.execute("INSERT OR IGNORE INTO tematica_grupo(hijo_id, padre_id) VALUES (?, ?)", (h, d)).rowcount:
                inf.append(f"temática: «{hija}» cuelga ahora de «{despues}»")
    # Que toda obra tenga los grupos de sus temáticas y avisos (Relación de pareja → Relaciones…)
    for t in ("tematica", "aviso"):
        db.execute(f"INSERT OR IGNORE INTO obra_{t}(obra_id, {t}_id) SELECT x.obra_id, a.padre_id FROM obra_{t} x "
                   f"JOIN {t}_ancestro a ON a.hijo_id = x.{t}_id")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default=str(DB_DEFECTO))
    ap.add_argument("--simular", action="store_true")
    a = ap.parse_args()
    db = sqlite3.connect(a.db)
    db.execute("PRAGMA foreign_keys = ON")
    if not a.simular:
        copia = COPIAS / f"safoteca_antes_etiquetas_{datetime.now():%Y%m%d_%H%M%S}.db"
        copia.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(a.db, copia)
        print("Copia de seguridad:", copia)
    inf = []
    aplicar(db, inf)
    print("\n".join(inf) or "Nada que cambiar: ya estaba hecho.")
    if a.simular:
        db.rollback()
        print("\n(Simulación: no se ha guardado nada.)")
    else:
        db.commit()
        print("\nListo. Ahora ejecuta tools/exportar_json.py y tools/generar_formulario.py")


if __name__ == "__main__":
    sys.exit(main())
