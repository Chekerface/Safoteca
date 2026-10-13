#!/usr/bin/env python3
"""Exporta a JSON lo que se publica en la web: solo películas y series con estado 'publicada'.

Nunca se exportan: estado, alias de revisoras, notas internas ni la URL de origen del póster.
Solo usa la librería estándar de Python (funciona en cualquier sitio).

Uso:
    python tools/exportar_json.py
Genera web/data/obras.json y web/data/catalogos.json
"""
import argparse, csv, json, sqlite3
from datetime import datetime, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from importar_excel import asegurar_esquema  # noqa: E402
from plataformas import reconocer  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent

SQL_GENEROS = """SELECT g.nombre FROM obra_genero x JOIN genero g ON g.id = x.genero_id
                 WHERE x.obra_id = ? ORDER BY g.nombre"""
SQL_TEMATICAS = """SELECT t.nombre FROM obra_tematica x JOIN tematica t ON t.id = x.tematica_id
                   WHERE x.obra_id = ? ORDER BY t.nombre"""
SQL_AVISOS = """SELECT a.nombre, a.categoria FROM obra_aviso x JOIN aviso a ON a.id = x.aviso_id
                WHERE x.obra_id = ? ORDER BY a.nombre"""
SQL_PERSONAS = """SELECT p.nombre FROM obra_persona x JOIN persona p ON p.id = x.persona_id
                  WHERE x.obra_id = ? AND x.rol = ? ORDER BY p.nombre"""
SQL_ENLACES = "SELECT url FROM obra_enlace WHERE obra_id = ? AND tipo = ? ORDER BY id"

# Catálogos para los filtros: solo lo que usan las obras publicadas
SQL_CAT_GENEROS = """SELECT DISTINCT g.nombre FROM genero g
                     JOIN obra_genero x ON x.genero_id = g.id
                     JOIN vista_publicable o ON o.id = x.obra_id ORDER BY g.nombre"""
SQL_CAT_TEMATICAS = """SELECT DISTINCT t.nombre FROM tematica t
                       JOIN obra_tematica x ON x.tematica_id = t.id
                       JOIN vista_publicable o ON o.id = x.obra_id ORDER BY t.nombre"""
SQL_CAT_AVISOS = """SELECT DISTINCT a.nombre, a.categoria FROM aviso a
                    JOIN obra_aviso x ON x.aviso_id = a.id
                    JOIN vista_publicable o ON o.id = x.obra_id ORDER BY a.categoria, a.nombre"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(RAIZ / "safoteca.db"))
    ap.add_argument("--salida", default=str(RAIZ / "web" / "data"))
    a = ap.parse_args()

    db = sqlite3.connect(a.db)
    asegurar_esquema(db)
    db.row_factory = sqlite3.Row
    salida = Path(a.salida)
    salida.mkdir(parents=True, exist_ok=True)

    def col(sql, *params):
        return [r[0] for r in db.execute(sql, params)]

    def avisos(sql, *params):
        return [{"nombre": r["nombre"], "categoria": r["categoria"]} for r in db.execute(sql, params)]

    def booleano(v):
        return None if v is None else bool(v)

    obras = []
    # Enlaces a Letterboxd: data/letterboxd.csv (id,url), que se rellena a mano
    letterboxd = {}
    ruta_lb = salida.parent.parent / "data" / "letterboxd.csv"
    if ruta_lb.exists():
        with open(ruta_lb, encoding="utf-8-sig", newline="") as f:
            for fila in csv.DictReader(f):
                if fila.get("url", "").strip().startswith("http"):
                    letterboxd[int(fila["id"])] = fila["url"].strip()
    consulta = "SELECT * FROM vista_publicable ORDER BY COALESCE(titulo_es, titulo_original) COLLATE NOCASE"
    for o in db.execute(consulta).fetchall():
        oid = o["id"]
        obras.append({
            "id": oid,
            "tipo": o["tipo"],
            "titulo": o["titulo_es"] or o["titulo_original"],
            "titulo_original": o["titulo_original"],
            "titulo_latam": o["titulo_latam"],
            "pais": o["pais"],
            "anio": o["anio"],
            "anio_fin": o["anio_fin"],
            "sinopsis": o["sinopsis"],
            "edad": o["edad_recomendada"],
            "relevancia": o["nivel_relevancia"],
            "temporadas": o["temporada_aparicion"],
            "disponible_espana": booleano(o["disponible_espana"]),
            "final_feliz": booleano(o["final_feliz"]),
            "poster": o["poster_archivo"] or (str(oid) if (salida.parent / "img" / f"{oid}_300.webp").exists() else None),  # nombre base: img/<poster>_300.webp e img/<poster>_600.webp
            "generos": col(SQL_GENEROS, oid),
            "tematicas": col(SQL_TEMATICAS, oid),
            "avisos": avisos(SQL_AVISOS, oid),
            "actrices": col(SQL_PERSONAS, oid, "actriz"),
            "directores": col(SQL_PERSONAS, oid, "director"),
            "donde_ver": col(SQL_ENLACES, oid, "donde_ver"),
            "plataformas": [dict(zip("npu", (*reconocer(u), u))) for u in col(SQL_ENLACES, oid, "donde_ver")],  # n=plataforma, p=país, u=enlace
            "info": col(SQL_ENLACES, oid, "info"),
            "letterboxd": letterboxd.get(oid),
            "publicada": o["publicada_el"],  # fecha UTC de publicación: desempata «Novedades»
        })

    catalogos = {
        "generos": col(SQL_CAT_GENEROS),
        "tematicas": col(SQL_CAT_TEMATICAS),
        "avisos": avisos(SQL_CAT_AVISOS),
    }
    meta = {"generado": datetime.now(timezone.utc).isoformat(timespec="seconds"), "total": len(obras)}
    (salida / "obras.json").write_text(
        json.dumps({"meta": meta, "obras": obras}, ensure_ascii=False, indent=1), encoding="utf-8")
    (salida / "catalogos.json").write_text(json.dumps(catalogos, ensure_ascii=False, indent=1), encoding="utf-8")
    # Lista pública de enlaces de póster de las obras publicadas: la usa GitHub Actions para descargarlos
    # (tools/posters_ci.py). Solo id, título y enlace de la imagen; nada privado.
    filas = db.execute(
        "SELECT id, COALESCE(titulo_es, titulo_original), poster_origen FROM obra "
        "WHERE id IN (SELECT id FROM vista_publicable) AND poster_origen IS NOT NULL AND poster_origen <> '' ORDER BY id").fetchall()
    destino = salida.parent.parent / "data" / "posters.csv"
    destino.parent.mkdir(parents=True, exist_ok=True)
    with open(destino, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "titulo", "url"])
        w.writerows([tuple(r) for r in filas])
    print(f"Exportadas {len(obras)} obras -> {salida}  ({len(filas)} pósters en {destino.name})")


if __name__ == "__main__":
    main()
