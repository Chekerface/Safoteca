#!/usr/bin/env python3
"""Carga en la base de datos las obras de la «Plantilla La Safoteca» rellena.

A diferencia de importar_excel.py (migración inicial, borra la base de datos),
este script AÑADE obras nuevas y ACTUALIZA las existentes. No borra nada.

Uso:
    python tools/importar_plantilla.py Plantilla_rellena.xlsx --simular   # solo informa, no guarda
    python tools/importar_plantilla.py Plantilla_rellena.xlsx             # guarda y regenera la web

Reglas (también están en docs/guia.md):
  * Se lee la hoja «Obras» por NOMBRE de cabecera (el asterisco da igual y el orden también).
  * Columna «Id» con valor  -> se actualiza esa obra.  Vacía -> se busca por tipo + título original
    (+ año); si ya existe se actualiza, si no se crea una nueva.
  * Una casilla vacía NO borra lo que ya hay en la base de datos. Los grupos (géneros, temáticas,
    avisos, actrices, directore, enlaces) se sustituyen enteros solo si en la fila hay algo escrito.
  * «Revisada = Sí» publica la obra si es película o serie y tiene sinopsis y nivel de relevancia;
    si no los tiene queda como «revisada» y se avisa. Nunca se despublica nada desde la plantilla.
  * Valores nuevos de temática/aviso/género se crean marcados como «pendiente de revisión».
  * Columna opcional «Letterboxd (enlace)»: se guarda en data/letterboxd.csv.
Antes de guardar se hace una copia de la base de datos en data/privado/copias/.
Las incidencias salen por pantalla y en informes/incidencias_plantilla.csv.
"""
import argparse, csv, shutil, sqlite3, subprocess, sys, unicodedata
from datetime import datetime
from pathlib import Path

import openpyxl

sys.path.insert(0, str(Path(__file__).resolve().parent))
from importar_excel import Importador, RAIZ, limpio, separar, a_entero  # noqa: E402

HOJA = "Plantilla"
TIPOS = {"pelicula": "pelicula", "película": "pelicula", "serie": "serie", "libro": "libro",
         "comic": "comic", "cómic": "comic"}


def norm(h):
    """Cabecera normalizada: sin asterisco, tildes, mayúsculas ni espacios dobles."""
    s = unicodedata.normalize("NFKD", str(h or "").replace("*", ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(s.lower().split())


def leer_filas(ws):
    it = ws.iter_rows(values_only=True)
    cab = [norm(c) for c in next(it)]
    for n, fila in enumerate(it, start=2):
        d = {}
        for h, v in zip(cab, fila):
            if h and h not in d:
                d[h] = v
        if any(limpio(v) for k, v in d.items() if k != "que falta"):
            yield n, d


def juntar(f, *claves):
    """Une varias casillas en un texto separado por comas."""
    partes = [limpio(f.get(norm(c))) for c in claves]
    return ", ".join(p for p in partes if p) or None


def grupo(f, prefijo, cuantas, extra):
    return juntar(f, *[f"{prefijo} {i}" for i in range(1, cuantas + 1)], extra)


class Plantilla:
    def __init__(self, db, informes):
        self.db = db
        self.imp = Importador(db, informes)
        for n, tw, desc in db.execute("SELECT nombre, es_tw, descripcion FROM aviso"):
            self.imp.tw_tags[n.lower()] = (tw, desc)
        self.oficiales = {t: {r[0] for r in db.execute(f"SELECT nombre FROM {t} WHERE pendiente_revision=0")}
                          for t in ("genero", "tematica", "aviso")}
        self.res = {"nuevas": [], "actualizadas": [], "publicadas": [], "omitidas": []}
        self.letterboxd = {}

    def inc(self, n, titulo, campo, valor, problema):
        self.imp.inc(HOJA, n, titulo, campo, valor, problema)

    # ------------------------------------------------------------ búsqueda
    def buscar(self, n, titulo, tipo, anio, oid_txt):
        if oid_txt:
            oid = a_entero(oid_txt)
            fila = self.db.execute("SELECT id FROM obra WHERE id=?", (oid,)).fetchone() if oid else None
            if not fila:
                self.inc(n, titulo, "Id", oid_txt, "no existe ese Id en la base de datos: fila no importada")
                return "error"
            return oid
        cand = self.db.execute(
            "SELECT id, anio FROM obra WHERE tipo=? AND lower(titulo_original)=lower(?)", (tipo, titulo)).fetchall()
        for oid, a in cand:
            if anio is None or a is None or a == anio:
                self.inc(n, titulo, "Id", None, f"ya existía (id {oid}): se actualiza esa obra en vez de crear otra")
                return oid
        return None

    # --------------------------------------------------------------- fila
    def fila(self, n, f):
        imp = self.imp
        tit_o = limpio(f.get("titulo original"))
        tit_es = limpio(f.get("titulo en espana"))
        titulo = tit_o or tit_es
        tipo_txt = (limpio(f.get("tipo")) or "").lower()
        if not titulo:
            return
        if not tit_o:
            self.inc(n, titulo, "Título original", None, "vacío: se usa el título en España")
        tipo = TIPOS.get(tipo_txt)
        if not tipo:
            self.inc(n, titulo, "Tipo", tipo_txt or None, "falta o no reconocido: fila no importada")
            self.res["omitidas"].append(titulo)
            return
        anio = fin = None
        if limpio(f.get("ano")):
            anio, _ = imp.anio(HOJA, n, titulo, f.get("ano"))
        if limpio(f.get("ano fin")):
            fin, _ = imp.anio(HOJA, n, titulo, f.get("ano fin"))
            if fin and anio and fin < anio:
                self.inc(n, titulo, "Año fin", fin, "anterior al año de inicio: se ignora")
                fin = None
        oid = self.buscar(n, titulo, tipo, anio, limpio(f.get("id")))
        if oid == "error":
            self.res["omitidas"].append(titulo)
            return

        campos = {"tipo": tipo, "titulo_original": titulo, "titulo_es": tit_es,
                  "titulo_latam": limpio(f.get("titulo en latinoamerica")), "pais": limpio(f.get("pais")),
                  "anio": anio, "anio_fin": fin, "sinopsis": limpio(f.get("sinopsis")),
                  "temporada_aparicion": limpio(f.get("temporada de aparicion"))}
        if limpio(f.get("edad recomendada")):
            campos["edad_recomendada"] = imp.edad(HOJA, n, titulo, f.get("edad recomendada"))
        if limpio(f.get("nivel de relevancia")):
            campos["nivel_relevancia"] = imp.relevancia(HOJA, n, titulo, f.get("nivel de relevancia"))
        if limpio(f.get("disponible en espana")):
            campos["disponible_espana"] = imp.si_no(HOJA, n, titulo, "disponible_espana", f.get("disponible en espana"))
        if limpio(f.get("final feliz")):
            campos["final_feliz"] = imp.si_no(HOJA, n, titulo, "final_feliz", f.get("final feliz"))
        poster = limpio(f.get("poster (enlace de la imagen)"))
        if poster:
            campos["poster_origen"] = imp.poster(poster)
            if not campos["poster_origen"]:
                self.inc(n, titulo, "Póster", poster, "no es un enlace http(s): se ignora")
        rev = limpio(f.get("revisore"))
        if rev:
            campos["revisora_alias"] = imp.alias_de(rev) if "@" in rev else rev
        campos = {k: v for k, v in campos.items() if v is not None}

        if oid is None:
            if "sinopsis" not in campos:
                self.inc(n, titulo, "Sinopsis", None, "vacía: la obra queda en borrador hasta completarla")
            if "nivel_relevancia" not in campos:
                self.inc(n, titulo, "Nivel de relevancia", None, "vacío: la obra queda en borrador hasta completarlo")
            cols = list(campos)
            cur = self.db.execute(f"INSERT INTO obra ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
                                  [campos[c] for c in cols])
            oid = cur.lastrowid
            self.res["nuevas"].append((oid, titulo))
        else:
            sets = ",".join(f"{c}=?" for c in campos)
            self.db.execute(f"UPDATE obra SET {sets} WHERE id=?", [*campos.values(), oid])
            self.res["actualizadas"].append((oid, titulo))

        # --- grupos
        gen = juntar(f, "Género 1", "Género 2")
        tem = grupo(f, "Temática", 12, "Otras temáticas (separadas por comas)")
        avi = grupo(f, "Aviso", 10, "Otros avisos (separados por comas)")
        if gen:
            self.db.execute("DELETE FROM obra_genero WHERE obra_id=?", (oid,))
            imp.vincular_lista(oid, gen, "genero", "obra_genero", "genero_id", imp.map_gen, self.oficiales["genero"])
        if tem:
            self.db.execute("DELETE FROM obra_tematica WHERE obra_id=?", (oid,))
            imp.vincular_lista(oid, tem, "tematica", "obra_tematica", "tematica_id", imp.map_tem, self.oficiales["tematica"])
        if avi:
            self.db.execute("DELETE FROM obra_aviso WHERE obra_id=?", (oid,))
            imp.vincular_lista(oid, avi, "aviso", "obra_aviso", "aviso_id", imp.map_avi, self.oficiales["aviso"])
        for clave, rol in (("actrices (separadas por comas)", "actriz"), ("directore", "director")):
            if limpio(f.get(clave)):
                self.db.execute("DELETE FROM obra_persona WHERE obra_id=? AND rol=?", (oid, rol))
                imp.vincular_personas(oid, f.get(clave), rol)
        ver = juntar(f, "Dónde verla (enlace)", "Dónde verla (enlace 2)")
        if ver:
            self.db.execute("DELETE FROM obra_enlace WHERE obra_id=? AND tipo='donde_ver'", (oid,))
            imp.vincular_enlaces(oid, ver, "donde_ver")
        if limpio(f.get("enlace informativo")):
            self.db.execute("DELETE FROM obra_enlace WHERE obra_id=? AND tipo='info'", (oid,))
            imp.vincular_enlaces(oid, f.get("enlace informativo"), "info")

        # --- Letterboxd
        lb = limpio(f.get("letterboxd (enlace)")) or limpio(f.get("letterboxd"))
        if lb:
            if lb.lower().startswith("http") and "letterboxd.com" in lb.lower():
                self.letterboxd[oid] = (titulo, lb.replace("http://", "https://", 1))
            else:
                self.inc(n, titulo, "Letterboxd", lb, "no es un enlace de letterboxd.com: se ignora")

        # --- estado
        if (limpio(f.get("revisada")) or "").lower() in ("si", "sí", "true", "x"):
            actual = self.db.execute("SELECT estado FROM obra WHERE id=?", (oid,)).fetchone()[0]
            if actual == "borrador":
                self.db.execute("UPDATE obra SET estado='revisada' WHERE id=?", (oid,))
            if tipo in ("pelicula", "serie") and actual != "publicada":
                try:
                    self.db.execute("UPDATE obra SET estado='publicada' WHERE id=?", (oid,))
                    self.res["publicadas"].append((oid, titulo))
                except sqlite3.IntegrityError:
                    self.inc(n, titulo, "Revisada", "Sí", "no se publica: falta sinopsis o nivel de relevancia")
            elif tipo not in ("pelicula", "serie"):
                self.inc(n, titulo, "Revisada", "Sí", "libros y cómics no se publican todavía en la web: queda como revisada")

    # ---------------------------------------------------------- letterboxd
    def guardar_letterboxd(self):
        ruta = RAIZ / "data" / "letterboxd.csv"
        filas = {}
        if ruta.exists():
            with open(ruta, encoding="utf-8", newline="") as fh:
                for r in csv.DictReader(fh):
                    filas[int(r["id"])] = (r["titulo"], r["url"])
        filas.update(self.letterboxd)
        with open(ruta, "w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["id", "titulo", "url"])
            for oid in sorted(filas):
                w.writerow([oid, *filas[oid]])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("excel")
    ap.add_argument("--db", default=str(RAIZ / "safoteca.db"))
    ap.add_argument("--simular", action="store_true", help="no guarda nada: solo muestra qué pasaría")
    ap.add_argument("--sin-exportar", action="store_true", help="no regenera web/data después de guardar")
    a = ap.parse_args()

    dbp = Path(a.db)
    if not dbp.exists():
        sys.exit(f"No encuentro la base de datos {dbp}")
    wb = openpyxl.load_workbook(a.excel, data_only=True, read_only=True)
    hoja = next((w for w in wb.worksheets if w.title.strip().lower() == "obras"), None)
    if hoja is None:
        sys.exit("El Excel no tiene una hoja llamada «Obras»: ¿es la plantilla?")

    if not a.simular:
        copias = RAIZ / "data" / "privado" / "copias"
        copias.mkdir(parents=True, exist_ok=True)
        copia = copias / f"safoteca_{datetime.now():%Y%m%d_%H%M%S}.db"
        shutil.copy2(dbp, copia)
        print(f"Copia de seguridad: {copia.relative_to(RAIZ)}")

    db = sqlite3.connect(dbp)
    db.execute("PRAGMA foreign_keys = ON")
    pl = Plantilla(db, RAIZ / "informes")
    n_filas = 0
    for n, f in leer_filas(hoja):
        n_filas += 1
        try:
            pl.fila(n, f)
        except sqlite3.IntegrityError as e:
            pl.inc(n, limpio(f.get("titulo original")) or "", "fila", None, f"no se pudo guardar: {e}")
            pl.res["omitidas"].append(limpio(f.get("titulo original")))

    (RAIZ / "informes").mkdir(exist_ok=True)
    with open(RAIZ / "informes" / "incidencias_plantilla.csv", "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["hoja", "fila", "obra", "campo", "valor", "problema"])
        w.writerows(pl.imp.incidencias)

    r = pl.res
    print(f"\n=== {'SIMULACIÓN' if a.simular else 'Importación'}: {n_filas} filas leídas ===")
    print(f"  nuevas:       {len(r['nuevas'])}  {[t for _, t in r['nuevas']]}")
    print(f"  actualizadas: {len(r['actualizadas'])}  {[t for _, t in r['actualizadas']]}")
    print(f"  publicadas:   {len(r['publicadas'])}  {[t for _, t in r['publicadas']]}")
    print(f"  omitidas:     {len(r['omitidas'])}  {r['omitidas']}")
    nuevos = {t: [x[0] for x in db.execute(f"SELECT nombre FROM {t} WHERE pendiente_revision=1")] for t in ("genero", "tematica", "aviso")}
    for t, v in nuevos.items():
        if v:
            print(f"  {t}s pendientes de revisión: {v}")
    print(f"  incidencias: {len(pl.imp.incidencias)}")
    for i in pl.imp.incidencias:
        print("   -", f"fila {i[1]} · {i[2]} · {i[3]}: {i[5]}")

    if a.simular:
        db.rollback()
        db.close()
        print("\n(Simulación: no se ha guardado nada.)")
        return
    db.commit()
    db.close()
    if pl.letterboxd:
        pl.guardar_letterboxd()
        print(f"  Letterboxd: {len(pl.letterboxd)} enlaces guardados")
    if not a.sin_exportar:
        subprocess.run([sys.executable, str(RAIZ / "tools" / "exportar_json.py")], check=True)
    print("\nListo. Revisa los cambios con «git status», haz commit y sube a GitHub.")


if __name__ == "__main__":
    main()
