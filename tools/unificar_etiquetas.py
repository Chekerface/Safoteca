#!/usr/bin/env python3
"""Unifica temáticas y avisos según las decisiones del Excel de revisión (octubre 2026).

Tres tipos de operación, siempre sobre la base de datos:
  unir     X -> Y   Las obras que tenían X pasan a tener Y y X desaparece. Si Y no existe, X se renombra.
  anadir   X => Y   Las obras que tienen X reciben también Y (X se queda). Y se crea si no existe.
  renombrar X -> Y  Solo cambia el nombre (p. ej. mayúsculas).
  eliminar  X       Quita la etiqueta de la lista, pero solo si ninguna obra la usa.

Uso:
    python tools/unificar_etiquetas.py --simular   # solo informa
    python tools/unificar_etiquetas.py             # guarda (hace antes una copia de la base de datos)
Después: python tools/exportar_json.py y python tools/generar_formulario.py
Es seguro repetirlo: lo que ya está hecho no se vuelve a tocar.
"""
import argparse, shutil, sqlite3, sys
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

# (tabla, operación, origen, destino). El orden importa: primero se unen variantes y luego se añaden etiquetas.
OPERACIONES = [
    # ---- Temáticas
    ("tematica", "unir", "Adolescentes", "Adolescencia"),
    ("tematica", "unir", "Biografía", "Biográfico"),
    ("tematica", "anadir", "Bisexual", "Bisexualidad"),
    ("tematica", "unir", "Transexualidad", "Trans"),
    ("tematica", "unir", "Transgénero", "Trans"),
    ("tematica", "unir", "Vampiros", "Vampiras"),
    ("tematica", "unir", "Los 80", "Años 80"),
    ("tematica", "unir", "Los 90", "Años 90"),
    ("tematica", "unir", "Los 90 tm", "Años 90"),
    ("tematica", "anadir", "Brujas", "Brujería"),
    ("tematica", "unir", "Deporte", "Deportes"),
    ("tematica", "unir", "Horror corporal", "Body Horror"),
    ("tematica", "unir", "Policíaco", "Policíaca"),
    ("tematica", "unir", "Thriler", "Thriller"),
    ("tematica", "unir", "Thiller Psicológico", "Thriller psicológico"),
    ("tematica", "unir", "Relaciones perjudiciales", "Pareja tóxica"),
    ("tematica", "renombrar", "Pareja Idiota", "Pareja idiota"),
    ("tematica", "renombrar", "Pareja Sana", "Pareja sana"),
    # ---- Avisos
    ("aviso", "unir", "Madre lgtbófoba", "Madre lgbtfóbica"),
    ("aviso", "renombrar", "Sangre/gore", "Sangre/Gore"),
    ("aviso", "unir", "Sexualizado", "Sexualización"),
    ("aviso", "unir", "Alcohol", "Consumo de alcohol"),
    ("aviso", "unir", "Alcolismo", "Alcoholismo"),
    ("aviso", "anadir", "Alcoholismo", "Consumo de alcohol"),
    ("aviso", "unir", "Drogas", "Consumo de drogas"),
    ("aviso", "unir", "Adicción", "Drogodependencia"),
    ("aviso", "anadir", "Drogodependencia", "Consumo de drogas"),
    ("aviso", "unir", "Horror corporal", "Body Horror"),
    ("aviso", "unir", "Relaciones perjudiciales", "Pareja tóxica"),
    ("aviso", "unir", "Sexo esplícito", "Sexo Explícito"),
    ("aviso", "anadir", "Tiroteo escolar", "Tiroteo"),
    ("aviso", "unir", "Abuso animal", "Maltrato animal"),
    ("aviso", "unir", "Bullying", "Acoso escolar"),
    ("aviso", "anadir", "Acoso escolar", "Acoso"),
    ("aviso", "unir", "Agresión sexual", "Abuso sexual"),
    ("aviso", "anadir", "Genocidio", "Crímenes de guerra"),
    ("aviso", "anadir", "Ideas suicidas", "Depresión"),
    ("aviso", "unir", "Intento de violación", "Intento de abuso sexual"),
    # ---- Segunda tanda (respuestas del 19 de octubre)
    ("tematica", "anadir", "Lesbianismo", "Lesbiana"),
    ("aviso", "unir", "Madre lgbtfoba", "Madre lgbtfóbica"),
    ("aviso", "unir", "Relación tóxica", "Pareja tóxica"),
    ("aviso", "renombrar", "Pareja Tóxica", "Pareja tóxica"),
    ("tematica", "unir", "Drogas", "Consumo de drogas"),
    ("tematica", "anadir", "Drogodependencia", "Consumo de drogas"),
    ("aviso", "unir", "Cuernos", "Infidelidad"),
    # ---- Tercera tanda (columna «Decisión» del listado del 19 de octubre)
    ("tematica", "unir", "Aventura", "Aventuras"),
    ("tematica", "unir", "Bullying", "Acoso escolar"),
    ("tematica", "renombrar", "Ciencia Ficción", "Ciencia ficción"),
    ("tematica", "renombrar", "Comedia de Enredo", "Comedia de enredo"),
    ("tematica", "renombrar", "Comedia Dramática", "Comedia dramática"),
    ("tematica", "renombrar", "Comedia Española", "Comedia española"),
    ("tematica", "renombrar", "Cómic Juvenil", "Cómic juvenil"),
    ("tematica", "renombrar", "Drama Adolescente", "Drama adolescente"),
    ("tematica", "unir", "Erotismo", "Erótico"),
    ("tematica", "renombrar", "Fantasía Oscura", "Fantasía oscura"),
    ("tematica", "renombrar", "Friends to Lovers", "Friends to lovers"),
    ("tematica", "unir", "Futuro postapocalíptico", "Postapocalíptico"),
    ("aviso", "unir", "Mentiras y Engaño", "Engaños y Mentiras"),
    ("aviso", "unir", "Padre lgbtfobo", "Padre lgbtfóbico"),
    ("aviso", "unir", "Padre lgtbfobo", "Padre lgbtfóbico"),
    # Se quitan de la lista solo si no las usa ninguna obra
    *[("tematica", "eliminar", x, None) for x in (
        '"Cosas de chicas"', "A fuego lento", "BD", "De amigas a amantes", "De enemigas a amantes",
        "Entrada en la madurez", "Erótico-festivo", "Humor", "Manga", "Romance de instituto",
        "Romance en el trabajo", "Viaje en carretera", "Young Adult")],
]

TABLAS = {"tematica": "obra_tematica", "aviso": "obra_aviso"}


def ident(db, tabla, nombre):
    r = db.execute(f"SELECT id, nombre FROM {tabla} WHERE nombre = ?", (nombre,)).fetchone()  # NOCASE
    return r


def aplicar(db, informe):
    for tabla, op, origen, destino in OPERACIONES:
        enlace = TABLAS[tabla]
        col = tabla + "_id"
        o = ident(db, tabla, origen)
        d = ident(db, tabla, destino)
        et = "temática" if tabla == "tematica" else "aviso"
        if op == "eliminar":
            if o:
                n = db.execute(f"SELECT COUNT(*) FROM {enlace} WHERE {col} = ?", (o[0],)).fetchone()[0]
                if n:
                    informe.append(f"{et}: «{origen}» NO se elimina porque la usan {n} obras")
                else:
                    db.execute(f"DELETE FROM {tabla} WHERE id = ?", (o[0],))
                    informe.append(f"{et}: «{origen}» eliminada de la lista (0 obras)")
            continue
        if op == "renombrar":
            if o and o[1] != destino:
                db.execute(f"UPDATE {tabla} SET nombre = ? WHERE id = ?", (destino, o[0]))
                informe.append(f"{et}: «{origen}» renombrada a «{destino}»")
            continue
        if not o:
            informe.append(f"{et}: «{origen}» no existe (ya estaba hecho o no hay obras)")
            continue
        n = db.execute(f"SELECT COUNT(*) FROM {enlace} WHERE {col} = ?", (o[0],)).fetchone()[0]
        if op == "unir":
            if not d or d[0] == o[0]:
                db.execute(f"UPDATE {tabla} SET nombre = ? WHERE id = ?", (destino, o[0]))
                informe.append(f"{et}: «{origen}» renombrada a «{destino}» ({n} obras)")
            else:
                db.execute(f"INSERT OR IGNORE INTO {enlace}(obra_id, {col}) SELECT obra_id, ? FROM {enlace} WHERE {col} = ?", (d[0], o[0]))
                db.execute(f"DELETE FROM {enlace} WHERE {col} = ?", (o[0],))
                db.execute(f"DELETE FROM {tabla} WHERE id = ?", (o[0],))
                informe.append(f"{et}: «{origen}» unida a «{destino}» ({n} obras)")
        elif op == "anadir":
            if not d:
                db.execute(f"INSERT INTO {tabla}(nombre) VALUES (?)", (destino,))
                d = ident(db, tabla, destino)
            antes = db.execute(f"SELECT COUNT(*) FROM {enlace} WHERE {col} = ?", (d[0],)).fetchone()[0]
            db.execute(f"INSERT OR IGNORE INTO {enlace}(obra_id, {col}) SELECT obra_id, ? FROM {enlace} WHERE {col} = ?", (d[0], o[0]))
            despues = db.execute(f"SELECT COUNT(*) FROM {enlace} WHERE {col} = ?", (d[0],)).fetchone()[0]
            informe.append(f"{et}: las {n} obras con «{origen}» reciben también «{destino}» ({despues - antes} nuevas)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default=str(RAIZ / "safoteca.db"))
    ap.add_argument("--simular", action="store_true")
    a = ap.parse_args()
    db = sqlite3.connect(a.db)
    db.execute("PRAGMA foreign_keys = ON")
    if not a.simular:
        copia = RAIZ / "data" / "privado" / "copias" / f"safoteca_antes_unificar_{datetime.now():%Y%m%d_%H%M%S}.db"
        copia.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(a.db, copia)
        print("Copia de seguridad:", copia.relative_to(RAIZ))
    informe = []
    aplicar(db, informe)
    print("\n".join(informe))
    if a.simular:
        db.rollback()
        print("\n(Simulación: no se ha guardado nada.)")
    else:
        db.commit()
        print("\nListo. Ahora ejecuta tools/exportar_json.py y tools/generar_formulario.py")


if __name__ == "__main__":
    sys.exit(main())
