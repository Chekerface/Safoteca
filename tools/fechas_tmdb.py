#!/usr/bin/env python3
"""Fechas exactas desde TMDB (The Movie Database) para ordenar «Novedades».

Para cada serie o película guarda en la base de datos (no se enseñan en la web):
  tmdb_id        «movie/123» o «tv/456»
  fecha_estreno  estreno (series: primer episodio)
  fecha_novedad  series: último episodio emitido; películas: el estreno. Es la que ordena «Novedades».

Cómo encuentra cada obra en TMDB, por este orden:
  1. el tmdb_id que ya tenga (lo trae la pantalla «Proponer una obra»);
  2. el enlace de IMDb (tt1234567) de su «Enlace informativo»;
  3. buscando el título original (y si no, el de España) con su año, solo si hay una coincidencia clara.
Lo que no encuentra o es dudoso NO se toca: sale en informes/fechas_tmdb.csv con los candidatos para revisarlo.

Uso (necesita la variable TMDB_TOKEN con el token de lectura de TMDB):
    python tools/fechas_tmdb.py --simular            # solo informa
    python tools/fechas_tmdb.py                      # obras sin tmdb_id o sin fechas (copia de la base antes)
    python tools/fechas_tmdb.py --series-en-emision  # además, pone al día las series que siguen emitiéndose
    python tools/fechas_tmdb.py --posters            # además, póster de TMDB para las obras que no tienen
    python tools/fechas_tmdb.py --direccion          # además, dirección de TMDB para las películas que no tienen
    python tools/fechas_tmdb.py --sugerir-actrices   # además, sugiere actrices (sin guardarlas) para las obras sin actrices
    python tools/fechas_tmdb.py --todas              # vuelve a comprobar todas
Después: python tools/exportar_json.py
"""
import argparse, csv, json, os, re, shutil, sqlite3, sys, time, unicodedata
import urllib.parse, urllib.request
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from rutas import DB_DEFECTO, COPIAS  # noqa: E402
from importar_excel import asegurar_esquema  # noqa: E402

API = "https://api.themoviedb.org/3"
# Correcciones a mano para las que no encuentra o encuentra mal: Safoteca-datos/tmdb_manual.csv con columnas
# id,tmdb (p. ej. «42,movie/290098»). Se copia el id de TMDB de la dirección de su ficha (themoviedb.org/movie/290098).
MANUAL = {}
POSTER = "https://image.tmdb.org/t/p/w780"


class TMDB:
    def __init__(self, token, pausa=0.03):
        self.token, self.pausa, self.llamadas = token, pausa, 0

    def get(self, ruta, **params):
        params.setdefault("language", "es-ES")
        cab = {"accept": "application/json"}
        if len(self.token) > 60:
            cab["Authorization"] = "Bearer " + self.token
        else:
            params["api_key"] = self.token
        url = f"{API}{ruta}?{urllib.parse.urlencode(params)}"
        for intento in range(4):
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers=cab), timeout=20) as r:
                    self.llamadas += 1
                    time.sleep(self.pausa)
                    return json.load(r)
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    return None
                if e.code == 429 or e.code >= 500:
                    time.sleep(2 * (intento + 1))
                    continue
                raise
            except urllib.error.URLError:
                time.sleep(2 * (intento + 1))
        raise RuntimeError(f"TMDB no responde: {ruta}")


def norm(s):
    s = "".join(c for c in unicodedata.normalize("NFKD", s or "") if not unicodedata.combining(c)).casefold()
    s = re.sub(r"\b(the series|la serie|series|serie)\b", " ", s)
    return re.sub(r"[^a-z0-9฀-๿぀-鿿가-힯]+", "", s)


def anio_de(f):
    return int(f[:4]) if f and re.match(r"\d{4}", f) else None


def detalle(api, tmdb_id):
    """{'fecha_estreno', 'fecha_novedad', 'poster', 'titulo'} de «movie/123» o «tv/456»."""
    d = api.get("/" + tmdb_id, append_to_response="aggregate_credits" if tmdb_id.startswith("tv/") else "credits")
    if not d:
        return None
    equipo = (d.get("credits") or {}).get("crew") or []
    direccion = list(dict.fromkeys(p["name"] for p in equipo if p.get("job") == "Director" and p.get("name")))
    reparto = ((d.get("aggregate_credits") or d.get("credits") or {}).get("cast") or [])
    actrices = [(p.get("id"), p.get("name")) for p in sorted(reparto, key=lambda p: p.get("order", 99)) if p.get("gender") == 1][:4]
    if tmdb_id.startswith("tv/"):
        ultimo = (d.get("last_episode_to_air") or {}).get("air_date") or d.get("last_air_date")
        estreno = d.get("first_air_date")
        return {"fecha_estreno": estreno or None, "fecha_novedad": ultimo or estreno or None,
                "poster": d.get("poster_path"), "titulo": d.get("name") or d.get("original_name"),
                "direccion": [c["name"] for c in d.get("created_by") or [] if c.get("name")], "actrices": actrices}
    estreno = d.get("release_date")
    return {"fecha_estreno": estreno or None, "fecha_novedad": estreno or None,
            "poster": d.get("poster_path"), "titulo": d.get("title") or d.get("original_title"), "direccion": direccion, "actrices": actrices}


def no_latino(t):
    return any(ch.isalpha() and "LATIN" not in unicodedata.name(ch, "") for ch in t or "")


def nombre_latino(api, pid, nombre):
    """Si TMDB da el nombre en otra escritura (tailandés, coreano…), busca su versión en letras latinas."""
    if not no_latino(nombre) or not pid:
        return nombre
    p = api.get(f"/person/{pid}", language="en-US") or {}
    for n in [p.get("name")] + (p.get("also_known_as") or []):
        if n and not no_latino(n):
            return n
    return nombre


def buscar(api, o, enlaces):
    """Devuelve (tmdb_id, cómo, candidatos). tmdb_id None si no hay una coincidencia clara."""
    tipo = "tv" if o["tipo"] == "serie" else "movie"
    if MANUAL.get(o["id"]):
        return MANUAL[o["id"]], "puesto a mano (tmdb_manual.csv)", []
    if o["tmdb_id"]:
        return o["tmdb_id"], "ya guardado", []
    for u in enlaces:
        m = re.search(r"\b(tt\d{5,10})\b", u or "")
        if m:
            f = api.get(f"/find/{m.group(1)}", external_source="imdb_id") or {}
            res = f.get("tv_results" if tipo == "tv" else "movie_results") or []
            if len(res) == 1:
                return f"{tipo}/{res[0]['id']}", "IMDb", []
    cands = []
    limpia = lambda t: re.sub(r"\s*[\(\[].*?[\)\]]\s*", " ", t or "").strip()   # «Skins (Temporadas 3 y 4)» → «Skins»
    nuestros = {norm(x) for x in (o["titulo_original"], o["titulo_es"], o["titulo_latam"],
                                  limpia(o["titulo_original"]), limpia(o["titulo_es"])) if x} - {""}
    for titulo in dict.fromkeys(x for x in (limpia(o["titulo_original"]), limpia(o["titulo_es"])) if x):
        params = {"query": titulo, "include_adult": "false"}
        if o["anio"]:
            params["first_air_date_year" if tipo == "tv" else "primary_release_year"] = o["anio"]
        res = (api.get(f"/search/{tipo}", **params) or {}).get("results") or []
        if not res and o["anio"]:          # a veces el año de TMDB difiere en uno: sin año y se filtra después
            params.pop("first_air_date_year", None); params.pop("primary_release_year", None)
            res = (api.get(f"/search/{tipo}", **params) or {}).get("results") or []
        buenos = []
        for r in res[:10]:
            nombres = {norm(r.get(k)) for k in ("name", "original_name", "title", "original_title")} - {""}
            a = anio_de(r.get("first_air_date") or r.get("release_date"))
            cands.append(f"{tipo}/{r['id']} {r.get('name') or r.get('title')} ({a})")
            if nombres & nuestros and (not o["anio"] or not a or abs(a - o["anio"]) <= 1):
                buenos.append(r)
        if len(buenos) == 1:
            return f"{tipo}/{buenos[0]['id']}", "título y año", []
        # un único resultado buscando con el año exacto (p. ej. el título original en coreano): se acepta
        if not buenos and o["anio"]:
            del_anio = [r for r in res if anio_de(r.get("first_air_date") or r.get("release_date")) == o["anio"]]
            if len(res) == 1 and len(del_anio) == 1:
                return f"{tipo}/{del_anio[0]['id']}", "único resultado de ese año", []
        if len(buenos) > 1:
            exactos = [r for r in buenos if anio_de(r.get("first_air_date") or r.get("release_date")) == o["anio"]]
            if len(exactos) == 1:
                return f"{tipo}/{exactos[0]['id']}", "título y año", []
            return None, "varias coincidencias", cands[:5]
    return None, "no encontrada", list(dict.fromkeys(cands))[:5]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default=str(DB_DEFECTO))
    ap.add_argument("--simular", action="store_true", help="no guarda nada")
    ap.add_argument("--todas", action="store_true", help="comprueba todas las obras, no solo las que faltan")
    ap.add_argument("--series-en-emision", action="store_true", help="pone al día fecha_novedad de las series sin año de fin")
    ap.add_argument("--posters", action="store_true", help="póster de TMDB para las obras sin enlace de póster")
    ap.add_argument("--sugerir-actrices", action="store_true",
                    help="para las obras sin actrices, sugiere las 4 primeras actrices de TMDB en el informe (NO las guarda: "
                         "en La Safoteca son las de los personajes sáficos, y eso hay que revisarlo a mano)")
    ap.add_argument("--direccion", action="store_true",
                    help="dirección de TMDB para las PELÍCULAS que no tienen (las series no: TMDB solo da quién la creó)")
    a = ap.parse_args()
    token = os.environ.get("TMDB_TOKEN", "").strip()
    if not token:
        sys.exit("Falta la variable TMDB_TOKEN (el token de lectura de TMDB).")
    api = TMDB(token)
    f = Path(a.db).parent / "tmdb_manual.csv"
    if f.exists():
        with open(f, encoding="utf-8-sig", newline="") as fh:
            for r in csv.DictReader(fh):
                if (r.get("id") or "").strip().isdigit() and re.fullmatch(r"(movie|tv)/\d+", (r.get("tmdb") or "").strip()):
                    MANUAL[int(r["id"])] = r["tmdb"].strip()
        print(f"Correcciones a mano: {len(MANUAL)} (tmdb_manual.csv)")

    db = sqlite3.connect(a.db)
    asegurar_esquema(db)
    db.row_factory = sqlite3.Row
    if not a.simular:
        copia = COPIAS / f"safoteca_antes_fechas_{datetime.now():%Y%m%d_%H%M%S}.db"
        copia.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(a.db, copia)
        print("Copia de seguridad:", copia)

    obras = db.execute("SELECT * FROM obra WHERE tipo IN ('serie','pelicula') ORDER BY id").fetchall()
    informe, sugerencias = [], []
    cambios = {"ok": 0, "dudosa": 0, "posters": 0, "actualizadas": 0, "direccion": 0, "actrices": 0}
    for o in obras:
        falta = not o["tmdb_id"] or not o["fecha_novedad"] or (MANUAL.get(o["id"]) and MANUAL[o["id"]] != o["tmdb_id"])
        en_emision = a.series_en_emision and o["tipo"] == "serie" and o["tmdb_id"] and not o["anio_fin"]
        sin_poster = a.posters and not (o["poster_origen"] or "").strip()
        sin_dir = a.direccion and o["tipo"] == "pelicula" and not db.execute(
            "SELECT 1 FROM obra_persona WHERE obra_id = ? AND rol = 'director'", (o["id"],)).fetchone()
        sin_act = a.sugerir_actrices and not db.execute(
            "SELECT 1 FROM obra_persona WHERE obra_id = ? AND rol = 'actriz'", (o["id"],)).fetchone()
        if not (a.todas or falta or en_emision or sin_poster or sin_dir or sin_act):
            continue
        titulo = o["titulo_es"] or o["titulo_original"]
        enlaces = [r[0] for r in db.execute("SELECT url FROM obra_enlace WHERE obra_id = ? AND tipo = 'info'", (o["id"],))]
        tid, como, cands = buscar(api, o, enlaces)
        if not tid:
            cambios["dudosa"] += 1
            informe.append([o["id"], titulo, o["anio"], "REVISAR: " + como, "", "", "", " | ".join(cands)])
            continue
        det = detalle(api, tid)
        if not det:
            cambios["dudosa"] += 1
            informe.append([o["id"], titulo, o["anio"], "REVISAR: el id de TMDB no existe", tid, "", "", ""])
            continue
        nuevos = {"tmdb_id": tid, "fecha_estreno": det["fecha_estreno"], "fecha_novedad": det["fecha_novedad"]}
        if sin_poster and det["poster"]:
            nuevos["poster_origen"] = POSTER + det["poster"]
            cambios["posters"] += 1
        sugeridas = [nombre_latino(api, pid, n) for pid, n in det.get("actrices") or []] if sin_act else []
        if sugeridas:
            cambios["actrices"] += 1
            sugerencias.append([o["id"], titulo, o["anio"], tid, ", ".join(sugeridas)])
        dir_nueva = []
        if sin_dir and det.get("direccion"):
            from importar_excel import nombre_persona
            for nombre in det["direccion"][:4]:
                nombre = nombre_persona(nombre)
                r = db.execute("SELECT id FROM persona WHERE nombre = ?", (nombre,)).fetchone()
                pid = r[0] if r else db.execute("INSERT INTO persona(nombre) VALUES (?)", (nombre,)).lastrowid
                db.execute("INSERT OR IGNORE INTO obra_persona(obra_id, persona_id, rol) VALUES (?, ?, 'director')", (o["id"], pid))
                dir_nueva.append(nombre)
            cambios["direccion"] += 1
        distintos = {k: v for k, v in nuevos.items() if v and v != o[k]}
        if distintos:
            sets = ", ".join(f"{k} = ?" for k in distintos)
            db.execute(f"UPDATE obra SET {sets} WHERE id = ?", [*distintos.values(), o["id"]])
            cambios["actualizadas"] += 1
        cambios["ok"] += 1
        informe.append([o["id"], titulo, o["anio"], f"ok ({como})", tid, det["fecha_estreno"] or "",
                        det["fecha_novedad"] or "", f"en TMDB: {det['titulo']}" + (" · póster de TMDB" if "poster_origen" in distintos else "")
                        + (" · dirección: " + ", ".join(dir_nueva) if dir_nueva else "")])

    (RAIZ / "informes").mkdir(exist_ok=True)
    with open(RAIZ / "informes" / "fechas_tmdb.csv", "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "obra", "año", "resultado", "tmdb", "fecha_estreno", "fecha_novedad", "notas / candidatos"])
        w.writerows(sorted(informe, key=lambda r: (not str(r[3]).startswith("REVISAR"), r[0])))
    print(f"{'SIMULACIÓN · ' if a.simular else ''}Encontradas: {cambios['ok']} · cambiadas: {cambios['actualizadas']} · "
          f"pósters nuevos: {cambios['posters']} · películas con dirección nueva: {cambios['direccion']} · "
          f"obras con actrices sugeridas: {cambios['actrices']} · para revisar: {cambios['dudosa']} · llamadas a TMDB: {api.llamadas}")
    for r in informe:
        if str(r[3]).startswith("REVISAR"):
            print(f"  - {r[0]} · {r[1]} ({r[2]}): {r[3][9:]}" + (f" → {r[7]}" if r[7] else ""))
    if sugerencias:
        with open(RAIZ / "informes" / "actrices_sugeridas.csv", "w", encoding="utf-8-sig", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["id", "obra", "año", "tmdb", "actrices sugeridas (TMDB)", "actrices que quedan (rellenar)"])
            w.writerows([r + [""] for r in sugerencias])
        print("Actrices sugeridas (sin guardar, para revisar): informes/actrices_sugeridas.csv")
        for r in sugerencias:
            print(f"  · {r[1]} ({r[2]}): {r[4]}")
    print("Detalle: informes/fechas_tmdb.csv")
    if a.simular:
        db.rollback()
        print("(Simulación: no se ha guardado nada.)")
    else:
        db.commit()


if __name__ == "__main__":
    sys.exit(main())
