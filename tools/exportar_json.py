#!/usr/bin/env python3
"""Exporta a JSON lo que se publica en la web: solo películas y series con estado 'publicada'.

Nunca se exportan: estado, alias de revisoras, notas internas ni la URL de origen del póster.
Solo usa la librería estándar de Python (funciona en cualquier sitio).

Uso:
    python tools/exportar_json.py
Genera web/data/obras.json y web/data/catalogos.json
"""
import argparse, json, sqlite3
from datetime import datetime, timezone
from pathlib import Path

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
            "poster": o["poster_archivo"],  # nombre base: img/<poster>_300.webp e img/<poster>_600.webp
            "generos": col(SQL_GENEROS, oid),
            "tematicas": col(SQL_TEMATICAS, oid),
            "avisos": avisos(SQL_AVISOS, oid),
            "actrices": col(SQL_PERSONAS, oid, "actriz"),
            "directores": col(SQL_PERSONAS, oid, "director"),
            "donde_ver": col(SQL_ENLACES, oid, "donde_ver"),
            "info": col(SQL_ENLACES, oid, "info"),
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
    print(f"Exportadas {len(obras)} obras -> {salida}")


if __name__ == "__main__":
    main()
