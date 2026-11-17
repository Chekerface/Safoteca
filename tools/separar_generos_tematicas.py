#!/usr/bin/env python3
"""Separa géneros y temáticas (17 de noviembre de 2026) y completa avisos desde temáticas.

Norma: el GÉNERO es qué tipo de obra es (drama, comedia, terror…) y la TEMÁTICA de qué trata. Un nombre solo puede
estar en una de las dos listas. Lo que hace, siempre sobre la base de datos:

  1. GENERO_SOLO: si una obra tiene ese nombre como temática, recibe el género, y la temática desaparece.
     Las temáticas que eran «hijas» de esos nombres (Drama médico → Drama, Slasher → Terror…) se quedan como
     temáticas, pero sus obras reciben el género (lista en data/mapeos/tematica_a_genero.csv, que usa también
     el importador).
  2. TEMATICA_SOLO: si una obra tiene ese nombre como género, recibe la temática, y el género desaparece.
     «Día a día» se une a «Costumbrismo».
  3. Avisos desde temáticas: si una temática es también un aviso aceptado (Racismo, Crimen…), toda obra con esa
     temática recibe el aviso, para que quien lo evite no se la encuentre.

Uso:
    python tools/separar_generos_tematicas.py --simular   # solo informa (con el detalle por obra en informes/)
    python tools/separar_generos_tematicas.py             # guarda (hace antes una copia de la base de datos)
Después: python tools/exportar_json.py y python tools/generar_formulario.py
Es seguro repetirlo.
"""
import argparse, csv, shutil, sqlite3, sys, unicodedata
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from rutas import DB_DEFECTO, COPIAS  # noqa: E402

MAPEOS = RAIZ / "data" / "mapeos"

# Nombre con la ortografía que queda (solo la primera letra en mayúscula)
GENERO_SOLO = ["Acción", "Animación", "Anime", "Biográfico", "Ciencia ficción", "Comedia", "Comedia dramática",
               "Comedia negra", "Comedia romántica", "Documental", "Drama", "Fantasía", "Fantástico",
               "Ficción sobrenatural", "Histórico", "Horror", "Intriga", "Musical", "Policíaca", "Reality", "Romance",
               "Sitcom", "Suspense", "Telenovela", "Terror", "Thriller", "Western"]
TEMATICA_SOLO = ["Costumbrismo", "Deportes", "Distopía"]
UNIR_TEMATICA = {"Día a día": "Costumbrismo"}


def k(x):
    return "".join(c for c in unicodedata.normalize("NFKD", x or "") if not unicodedata.combining(c)).casefold().strip()


def buscar(db, tabla, nombre):
    for i, n in db.execute(f"SELECT id, nombre FROM {tabla}"):
        if k(n) == k(nombre):
            return i, n
    return None


def asegurar(db, tabla, nombre):
    r = buscar(db, tabla, nombre)
    if r:
        if r[1] != nombre:
            db.execute(f"UPDATE {tabla} SET nombre = ?, pendiente_revision = 0 WHERE id = ?", (nombre, r[0]))
        return r[0]
    return db.execute(f"INSERT INTO {tabla}(nombre, pendiente_revision) VALUES (?, 0)", (nombre,)).lastrowid


def leer_csv(nombre):
    with open(MAPEOS / nombre, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def titulo(db, oid):
    r = db.execute("SELECT COALESCE(titulo_es, titulo_original) FROM obra WHERE id = ?", (oid,)).fetchone()
    return r[0] if r else str(oid)


def aplicar(db, informe, detalle):
    genero_solo = {k(g) for g in GENERO_SOLO}
    # temáticas hijas de un nombre que pasa a ser solo género → sus obras reciben ese género
    hijas = {}
    for r in leer_csv("grupos_tematicas.csv"):
        if k(r["grupo"]) in genero_solo and k(r["hijo"]) not in genero_solo:
            hijas[r["hijo"]] = next(g for g in GENERO_SOLO if k(g) == k(r["grupo"]))

    # 0 · Día a día → Costumbrismo (como temática y como género)
    for origen, destino in UNIR_TEMATICA.items():
        d = asegurar(db, "tematica", destino)
        for tabla, enlace in (("tematica", "obra_tematica"), ("genero", "obra_genero")):
            o = buscar(db, tabla, origen)
            if not o:
                continue
            obras = [x[0] for x in db.execute(f"SELECT obra_id FROM {enlace} WHERE {tabla}_id = ?", (o[0],))]
            for oid in obras:
                if db.execute("INSERT OR IGNORE INTO obra_tematica(obra_id, tematica_id) VALUES (?, ?)", (oid, d)).rowcount:
                    detalle.append((titulo(db, oid), "temática +", destino, f"antes {origen}"))
            db.execute(f"DELETE FROM {enlace} WHERE {tabla}_id = ?", (o[0],))
            db.execute(f"DELETE FROM {tabla} WHERE id = ?", (o[0],))
            informe.append(f"{'temática' if tabla == 'tematica' else 'género'} «{o[1]}» unida a la temática «{destino}» ({len(obras)} obras)")

    # 1 · Solo género
    for g in GENERO_SOLO:
        t = buscar(db, "tematica", g)
        if not t:
            continue
        gid = asegurar(db, "genero", g)
        obras = [x[0] for x in db.execute("SELECT obra_id FROM obra_tematica WHERE tematica_id = ?", (t[0],))]
        nuevas = 0
        for oid in obras:
            if db.execute("INSERT OR IGNORE INTO obra_genero(obra_id, genero_id) VALUES (?, ?)", (oid, gid)).rowcount:
                nuevas += 1
                detalle.append((titulo(db, oid), "género +", g, f"tenía la temática «{t[1]}»"))
        db.execute("DELETE FROM obra_tematica WHERE tematica_id = ?", (t[0],))
        db.execute("DELETE FROM tematica WHERE id = ?", (t[0],))   # sus grupos se borran en cascada
        informe.append(f"«{g}»: solo género · {len(obras)} obras tenían la temática, {nuevas} reciben el género")
    for hija, g in sorted(hijas.items()):
        t = buscar(db, "tematica", hija)
        if not t:
            continue
        gid = asegurar(db, "genero", g)
        n = 0
        for (oid,) in db.execute("SELECT obra_id FROM obra_tematica WHERE tematica_id = ?", (t[0],)).fetchall():
            if db.execute("INSERT OR IGNORE INTO obra_genero(obra_id, genero_id) VALUES (?, ?)", (oid, gid)).rowcount:
                n += 1
                detalle.append((titulo(db, oid), "género +", g, f"tiene la temática «{t[1]}»"))
        if n:
            informe.append(f"temática «{t[1]}» → sus obras reciben el género «{g}» ({n} nuevas)")

    # 2 · Solo temática
    for tnombre in TEMATICA_SOLO:
        g = buscar(db, "genero", tnombre)
        if not g:
            continue
        tid = asegurar(db, "tematica", tnombre)
        obras = [x[0] for x in db.execute("SELECT obra_id FROM obra_genero WHERE genero_id = ?", (g[0],))]
        nuevas = 0
        for oid in obras:
            if db.execute("INSERT OR IGNORE INTO obra_tematica(obra_id, tematica_id) VALUES (?, ?)", (oid, tid)).rowcount:
                nuevas += 1
                detalle.append((titulo(db, oid), "temática +", tnombre, f"tenía el género «{g[1]}»"))
        db.execute("DELETE FROM obra_genero WHERE genero_id = ?", (g[0],))
        db.execute("DELETE FROM genero WHERE id = ?", (g[0],))
        informe.append(f"«{tnombre}»: solo temática · {len(obras)} obras tenían el género, {nuevas} reciben la temática")

    # 3 · Avisos desde temáticas
    avisos = {k(r["nombre"]): r["nombre"] for r in leer_csv("avisos_aceptados.csv")}
    total = 0
    for tid, tn in db.execute("SELECT id, nombre FROM tematica").fetchall():
        if k(tn) not in avisos:
            continue
        aid = asegurar(db, "aviso", avisos[k(tn)])
        n = 0
        for (oid,) in db.execute("SELECT obra_id FROM obra_tematica WHERE tematica_id = ?", (tid,)).fetchall():
            if db.execute("INSERT OR IGNORE INTO obra_aviso(obra_id, aviso_id) VALUES (?, ?)", (oid, aid)).rowcount:
                n += 1
                detalle.append((titulo(db, oid), "aviso +", avisos[k(tn)], f"tiene la temática «{tn}»"))
        if n:
            informe.append(f"temática «{tn}» → {n} obras reciben el aviso «{avisos[k(tn)]}»")
        total += n
    informe.append(f"Avisos añadidos desde temáticas: {total}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default=str(DB_DEFECTO))
    ap.add_argument("--simular", action="store_true")
    a = ap.parse_args()
    db = sqlite3.connect(a.db)
    db.execute("PRAGMA foreign_keys = ON")
    if not a.simular:
        copia = COPIAS / f"safoteca_antes_separar_generos_{datetime.now():%Y%m%d_%H%M%S}.db"
        copia.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(a.db, copia)
        print("Copia de seguridad:", copia)
    informe, detalle = [], []
    aplicar(db, informe, detalle)
    print("\n".join(informe))
    (RAIZ / "informes").mkdir(exist_ok=True)
    with open(RAIZ / "informes" / "separar_generos_tematicas.csv", "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["obra", "cambio", "etiqueta", "motivo"])
        w.writerows(sorted(detalle))
    print(f"\nDetalle por obra ({len(detalle)} cambios): informes/separar_generos_tematicas.csv")
    if a.simular:
        db.rollback()
        print("(Simulación: no se ha guardado nada.)")
    else:
        db.commit()
        print("Listo. Ahora ejecuta tools/exportar_json.py y tools/generar_formulario.py")


if __name__ == "__main__":
    sys.exit(main())
