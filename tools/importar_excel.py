#!/usr/bin/env python3
"""Importa el Excel de Glide a la base de datos SQLite de La Safoteca.

Es una migración inicial: crea la base de datos desde cero. Después de importar,
la base de datos pasa a ser la fuente de verdad y el Excel ya no se usa.

Uso:
    python tools/importar_excel.py data/privado/Base_de_datos.xlsx
    python tools/importar_excel.py data/privado/Base_de_datos.xlsx --forzar --publicar-revisadas

Genera:
    safoteca.db                       base de datos
    informes/incidencias.csv          todo lo que hay que revisar a mano
    informes/catalogo_*.csv           catálogos con el nº de usos, para fusionar variantes
    data/privado/revisoras.csv        correo -> alias (privado, no se sube a GitHub)
"""
import argparse, csv, re, sqlite3, sys
from collections import Counter, OrderedDict
from pathlib import Path

import openpyxl

RAIZ = Path(__file__).resolve().parent.parent
EDADES_VALIDAS = {"TP", "7", "12", "13", "14", "15", "16", "18"}
URL_RE = re.compile(r"https?://[^\s,;<>\"']+")


# ---------------------------------------------------------------- utilidades
def asegurar_esquema(db):
    """Pone al día una base de datos antigua (columna publicada_el y sus triggers). Es seguro repetirlo."""
    cols = [r[1] for r in db.execute("PRAGMA table_info(obra)")]
    if cols and "publicada_el" not in cols:
        db.execute("ALTER TABLE obra ADD COLUMN publicada_el TEXT")
        db.execute("UPDATE obra SET publicada_el = creada_el WHERE estado = 'publicada'")
        db.commit()
    db.executescript((RAIZ / "db" / "schema.sql").read_text(encoding="utf-8"))


def limpio(v):
    """Texto sin espacios sobrantes; None si está vacío."""
    if v is None:
        return None
    s = str(v).replace(" ", " ").strip()
    return s or None


def separar(v):
    """Separa 'a, b\\nc (nota, nota)' respetando los paréntesis."""
    s = limpio(v)
    if not s:
        return []
    partes, actual, nivel = [], [], 0
    for ch in s:
        if ch == "(":
            nivel += 1
        elif ch == ")":
            nivel = max(0, nivel - 1)
        if ch in ",\n;" and nivel == 0:
            partes.append("".join(actual))
            actual = []
        else:
            actual.append(ch)
    partes.append("".join(actual))
    return [p.strip() for p in partes if p.strip()]


def nombre_persona(texto):
    """'Kieron Gillen (1-13; coguionista: 14-19)' -> 'Kieron Gillen'."""
    return texto.split("(")[0].strip()


def a_entero(v):
    s = limpio(v)
    if not s:
        return None
    try:
        return int(float(s))
    except ValueError:
        return None


def clave_similar(texto):
    """Clave para detectar variantes casi iguales: sin mayúsculas, tildes ni plural."""
    import unicodedata
    t = unicodedata.normalize("NFKD", texto.lower())
    t = "".join(c for c in t if not unicodedata.combining(c)).strip()
    return re.sub(r"(es|s)$", "", t)


def cargar_mapeo(nombre):
    ruta = RAIZ / "data" / "mapeos" / nombre
    mapa = {}
    if ruta.exists():
        with open(ruta, encoding="utf-8", newline="") as f:
            for fila in csv.DictReader(f):
                var, can = limpio(fila.get("variante")), limpio(fila.get("canonico"))
                if var:
                    mapa[var.lower()] = can  # canonico vacío = descartar
    return mapa


def tipo_desde_categoria(valor):
    s = (limpio(valor) or "").lower()
    s = s.replace("pwlícula", "película")
    if s.startswith("pel"):
        return "pelicula"
    if s.startswith("serie"):
        return "serie"
    return None


# ------------------------------------------------------------------ lectura
def filas(ws):
    """Itera las filas de una hoja como diccionarios con cabeceras normalizadas."""
    it = ws.iter_rows(values_only=True)
    cab = [limpio(c) or f"_col{i}" for i, c in enumerate(next(it))]
    for n, fila in enumerate(it, start=2):
        if any(c is not None and str(c).strip() for c in fila):
            yield n, dict(zip(cab, fila))


class Importador:
    def __init__(self, db, informes):
        self.db = db
        self.informes = informes
        self.incidencias = []
        self.alias = OrderedDict()
        self.map_gen = cargar_mapeo("generos.csv")
        self.map_tem = cargar_mapeo("tematicas.csv")
        self.map_avi = cargar_mapeo("avisos.csv")
        self.cat_aviso = {k: v for k, v in cargar_mapeo("avisos_categorias.csv").items()}
        self.generos_oficiales = set()
        self.tw_tags = {}  # nombre.lower() -> (es_tw, descripcion)
        self.uso = {"genero": Counter(), "tematica": Counter(), "aviso": Counter()}
        self.letterboxd = {}  # id -> (título, url) leído de la columna «Link a Letterboxd»

    def inc(self, hoja, fila, obra, campo, valor, problema):
        self.incidencias.append([hoja, fila, obra or "", campo, valor if valor is not None else "", problema])

    # ---------------------------------------------------------- catálogos
    def alias_de(self, correo):
        c = limpio(correo)
        if not c:
            return None
        c = c.lower()
        if c not in self.alias:
            self.alias[c] = f"R{len(self.alias) + 1:02d}"
        return self.alias[c]

    def id_catalogo(self, tabla, nombre, pendiente=0, **extra):
        cur = self.db.execute(f"SELECT id FROM {tabla} WHERE nombre = ?", (nombre,))
        r = cur.fetchone()
        if r:
            return r[0]
        cols = ["nombre", "pendiente_revision"] + list(extra)
        vals = [nombre, pendiente] + list(extra.values())
        cur = self.db.execute(
            f"INSERT INTO {tabla} ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})", vals)
        return cur.lastrowid

    def vincular_lista(self, obra_id, valor, tabla, enlace, col, mapa, oficiales=None):
        vistos = set()
        for crudo in separar(valor):
            nombre = crudo
            clave = crudo.lower()
            if clave in mapa:
                nombre = mapa[clave]
                if not nombre:
                    continue
            if nombre.lower() in vistos:
                continue
            vistos.add(nombre.lower())
            self.uso[tabla][nombre] += 1
            pend = 0 if (oficiales is None or nombre in oficiales) else 1
            extra = {}
            if tabla == "aviso":
                es_tw, desc = self.tw_tags.get(nombre.lower(), (None, None))
                extra = {"es_tw": es_tw, "descripcion": desc, "categoria": self.cat_aviso.get(nombre.lower())}
            cid = self.id_catalogo(tabla, nombre, pend, **extra)
            self.db.execute(f"INSERT OR IGNORE INTO {enlace} (obra_id, {col}) VALUES (?, ?)", (obra_id, cid))

    def vincular_personas(self, obra_id, valor, rol):
        for crudo in separar(valor):
            nombre = nombre_persona(crudo)
            if not nombre:
                continue
            cur = self.db.execute("SELECT id FROM persona WHERE nombre = ?", (nombre,))
            r = cur.fetchone()
            pid = r[0] if r else self.db.execute("INSERT INTO persona (nombre) VALUES (?)", (nombre,)).lastrowid
            self.db.execute("INSERT OR IGNORE INTO obra_persona (obra_id, persona_id, rol) VALUES (?,?,?)",
                            (obra_id, pid, rol))

    def vincular_enlaces(self, obra_id, valor, tipo):
        vistos = set()
        for url in URL_RE.findall(limpio(valor) or ""):
            if url not in vistos:
                vistos.add(url)
                self.db.execute("INSERT INTO obra_enlace (obra_id, tipo, url) VALUES (?,?,?)", (obra_id, tipo, url))

    # ------------------------------------------------------ normalizadores
    def edad(self, hoja, n, obra, v):
        s = limpio(v)
        if not s:
            return None
        if s.upper() == "TP":
            return "TP"
        m = re.search(r"\d+", s)
        if m and 0 <= int(m.group()) <= 18:
            return str(int(m.group()))
        self.inc(hoja, n, obra, "edad_recomendada", s, "valor no reconocido")
        return None

    def relevancia(self, hoja, n, obra, v):
        s = limpio(v)
        if not s:
            self.inc(hoja, n, obra, "nivel_relevancia", None, "vacío")
            return None
        if s.upper() in ("A", "B", "C"):
            return s.upper()
        self.inc(hoja, n, obra, "nivel_relevancia", s, "valor no reconocido")
        return None

    def si_no(self, hoja, n, obra, campo, v):
        s = limpio(v)
        if not s:
            return None
        k = s.lower().replace("í", "i")
        if k == "si":
            return 1
        if k == "no":
            return 0
        self.inc(hoja, n, obra, campo, s, "ambiguo: revisar a mano")
        return None

    def anio(self, hoja, n, obra, v):
        """Devuelve (año, año_fin). Admite '2019', '2013-2019' y '2019-'."""
        s = limpio(v)
        if not s:
            return None, None
        m = re.fullmatch(r"(\d{4})(?:\.0)?\s*(?:[-–]\s*(\d{4})?)?", s)
        if m:
            ini = int(m.group(1))
            fin = int(m.group(2)) if m.group(2) else None
            if 1890 <= ini <= 2100 and (fin is None or ini <= fin <= 2100):
                return ini, fin
        self.inc(hoja, n, obra, "anio", s, "año no válido")
        return None, None

    def estado(self, v):
        return "revisada" if (limpio(v) or "").lower() == "true" else "borrador"

    # --------------------------------------------------------- inserción
    def insertar_obra(self, d):
        cols = list(d)
        cur = self.db.execute(
            f"INSERT INTO obra ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})", list(d.values()))
        return cur.lastrowid

    def poster(self, v):
        s = limpio(v)
        return s if s and s.lower().startswith("http") else None

    # ------------------------------------------------------------- hojas
    def leer_tags(self, wb):
        for nombre_hoja in ("Tags", "Tags Comics"):
            ws = next((w for w in wb.worksheets if w.title.strip() == nombre_hoja), None)
            if not ws:
                continue
            for _, f in filas(ws):
                tag = limpio(f.get("TAG"))
                if not tag:
                    continue
                marca = (limpio(f.get("Es TW o no")) or "").upper()
                es_tw = 1 if marca == "TW" else None
                desc = limpio(f.get("Descripción"))
                antes = self.tw_tags.get(tag.lower())
                if antes is None or (es_tw == 1):
                    self.tw_tags[tag.lower()] = (es_tw, desc)

    def leer_generos(self, wb):
        ws = next((w for w in wb.worksheets if w.title.strip() == "Géneros"), None)
        if ws:
            for _, f in filas(ws):
                g = limpio(f.get("Generos"))
                if g:
                    self.generos_oficiales.add(g)
                    self.id_catalogo("genero", g, 0)

    def hoja_datos(self, ws):
        hoja = "Datos"
        titulos = Counter()
        n_ok = 0
        for n, f in filas(ws):
            orig, es = limpio(f.get("Título Original")), limpio(f.get("Título en España"))
            if not (orig or es):
                continue
            titulo = orig or es
            tipo = tipo_desde_categoria(f.get("Categoría"))
            if tipo is None:
                self.inc(hoja, n, titulo, "tipo", limpio(f.get("Categoría")), "categoría no reconocida: fila no importada")
                continue
            if limpio(f.get("Categoría")) not in ("Serie", "Película"):
                self.inc(hoja, n, titulo, "tipo", limpio(f.get("Categoría")), "corregido automáticamente")
            titulos[titulo.lower()] += 1
            anio, anio_fin = self.anio(hoja, n, titulo, f.get("Año"))
            d = dict(
                tipo=tipo, titulo_es=es, titulo_latam=limpio(f.get("Título en Latinoamérica")),
                titulo_original=titulo, pais=limpio(f.get("País de Origen")), anio=anio, anio_fin=anio_fin,
                sinopsis=limpio(f.get("Sinopsis")),
                edad_recomendada=self.edad(hoja, n, titulo, f.get("Edad recomendada")),
                nivel_relevancia=self.relevancia(hoja, n, titulo, f.get("Nivel de relevancia")),
                temporada_aparicion=limpio(f.get("Temporada aparición")),
                disponible_espana=self.si_no(hoja, n, titulo, "disponible_espana", f.get("¿Está disponible?")),
                final_feliz=1 if (limpio(f.get("Final Feliz")) or "").lower() == "true" else None,
                poster_origen=self.poster(f.get("Póster")),
                estado=self.estado(f.get("Revisado")),
                revisora_alias=self.alias_de(f.get("Nombre del revisore")),
            )
            if not d["sinopsis"]:
                self.inc(hoja, n, titulo, "sinopsis", None, "vacío")
            oid = self.insertar_obra(d)
            lb = limpio(f.get("Link a Letterboxd"))
            if lb and "letterboxd.com" in lb.lower():
                self.letterboxd[oid] = (titulo, lb.replace("http://", "https://", 1))
            self.vincular_lista(oid, f.get("Género"), "genero", "obra_genero", "genero_id", self.map_gen, self.generos_oficiales)
            self.vincular_lista(oid, f.get("Temática"), "tematica", "obra_tematica", "tematica_id", self.map_tem)
            self.vincular_lista(oid, f.get("TW"), "aviso", "obra_aviso", "aviso_id", self.map_avi)
            self.vincular_personas(oid, f.get("Actrices (Película y Serie)"), "actriz")
            self.vincular_personas(oid, f.get("Directore (Película)"), "director")
            self.vincular_enlaces(oid, f.get("Donde se encuentra"), "donde_ver")
            self.vincular_enlaces(oid, f.get("Links bibliográficos"), "info")
            n_ok += 1
        for t, c in titulos.items():
            if c > 1:
                self.inc(hoja, "", t, "titulo_original", t, f"título duplicado ({c} filas)")
        return n_ok

    def hoja_libros(self, ws):
        hoja = "Libros"
        n_ok = 0
        for n, f in filas(ws):
            orig, es = limpio(f.get("Título Original")), limpio(f.get("Título en España"))
            if not (orig or es):
                continue
            titulo = orig or es
            anio, anio_fin = self.anio(hoja, n, titulo, f.get("Año"))
            d = dict(
                tipo="libro", titulo_es=es, titulo_latam=limpio(f.get("Título en Latinoamérica")),
                titulo_original=titulo, pais=limpio(f.get("País de Origen")), anio=anio, anio_fin=anio_fin,
                sinopsis=limpio(f.get("Sinopsis")), coleccion=limpio(f.get("Categoría")),
                editorial=limpio(f.get("Editorial")), volumenes=limpio(f.get("Volúmenes de aparición")),
                edad_recomendada=self.edad(hoja, n, titulo, f.get("Edad recomendada")),
                nivel_relevancia=self.relevancia(hoja, n, titulo, f.get("Nivel de relevancia")),
                disponible_espana=self.si_no(hoja, n, titulo, "disponible_espana", f.get("¿Está disponible en España?")),
                poster_origen=self.poster(f.get("Póster")), estado="borrador",
                revisora_alias=self.alias_de(f.get("Nombre del revisore")),
            )
            oid = self.insertar_obra(d)
            self.vincular_lista(oid, f.get("Género"), "genero", "obra_genero", "genero_id", self.map_gen, self.generos_oficiales)
            self.vincular_lista(oid, f.get("Temática"), "tematica", "obra_tematica", "tematica_id", self.map_tem)
            self.vincular_lista(oid, f.get("TW"), "aviso", "obra_aviso", "aviso_id", self.map_avi)
            self.vincular_personas(oid, f.get("Autore (libro/comic)"), "autore")
            self.vincular_enlaces(oid, f.get("Donde se encuentra"), "donde_ver")
            self.vincular_enlaces(oid, f.get("Links bibliográficos"), "info")
            self.vincular_enlaces(oid, f.get("Link a GoodReads"), "info")
            n_ok += 1
        return n_ok

    def hoja_comics(self, ws):
        hoja = "Cómics"
        n_ok = 0
        for n, f in filas(ws):
            es = limpio(f.get("Título"))
            orig = limpio(f.get("Título Original"))
            if not (orig or es):
                continue
            titulo = orig or es
            if not orig:
                self.inc(hoja, n, titulo, "titulo_original", None, "vacío: se usa el título en español")
            anio, anio_fin = self.anio(hoja, n, titulo, f.get("Año de publicación (en España)"))
            d = dict(
                tipo="comic", titulo_es=es, titulo_original=titulo, pais=limpio(f.get("Nacionalidad")),
                anio=anio, anio_fin=anio_fin, sinopsis=limpio(f.get("Sinopsis")),
                coleccion=limpio(f.get("Colección")), editorial=limpio(f.get("Editorial española")),
                volumenes=limpio(f.get("Nº vols.")),
                edad_recomendada=self.edad(hoja, n, titulo, f.get("Edad recomendada")),
                nivel_relevancia=self.relevancia(hoja, n, titulo, f.get("Categoría (A, B, C)")),
                disponible_espana=self.si_no(hoja, n, titulo, "disponible_espana", f.get("¿Publicado en España?")),
                poster_origen=self.poster(f.get("Cubierta/s")), estado="borrador",
                revisora_alias=self.alias_de(f.get("Nombre del revisore")),
            )
            oid = self.insertar_obra(d)
            self.vincular_lista(oid, f.get("Género"), "genero", "obra_genero", "genero_id", self.map_gen, self.generos_oficiales)
            self.vincular_lista(oid, f.get("Temática"), "tematica", "obra_tematica", "tematica_id", self.map_tem)
            self.vincular_lista(oid, f.get("Trigger Warning"), "aviso", "obra_aviso", "aviso_id", self.map_avi)
            for col, rol in (("Autore único", "autore"), ("Guionista", "guionista"), ("Dibujante", "dibujante"),
                             ("Entintador", "entintador"), ("Colorista", "colorista")):
                self.vincular_personas(oid, f.get(col), rol)
            self.vincular_enlaces(oid, f.get("Disponible en"), "donde_ver")
            self.vincular_enlaces(oid, f.get("Links bibliográficos"), "info")
            n_ok += 1
        return n_ok

    def unificar_mayusculas(self):
        """'Drama' y 'drama' son la misma etiqueta: se queda la grafía más usada."""
        for tabla in ("genero", "tematica", "aviso"):
            if tabla != "genero":  # los géneros oficiales conservan su grafía
                grupos = {}
                for nombre, veces in self.uso[tabla].items():
                    grupos.setdefault(nombre.lower(), []).append((veces, nombre))
                for variantes in grupos.values():
                    if len(variantes) > 1:
                        mejor = max(variantes, key=lambda x: (x[0], x[1][:1].isupper()))[1]
                        self.db.execute(f"UPDATE {tabla} SET nombre = ? WHERE nombre = ?", (mejor, mejor))
            nuevo = Counter()
            for nombre, veces in self.uso[tabla].items():
                fila = self.db.execute(f"SELECT nombre FROM {tabla} WHERE nombre = ?", (nombre,)).fetchone()
                nuevo[fila[0] if fila else nombre] += veces
            self.uso[tabla] = nuevo

    # ----------------------------------------------------------- informes
    def escribir_informes(self):
        self.informes.mkdir(parents=True, exist_ok=True)
        with open(self.informes / "incidencias.csv", "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(["hoja", "fila", "obra", "campo", "valor", "problema"])
            w.writerows(self.incidencias)
        for tabla in ("genero", "tematica", "aviso"):
            with open(self.informes / f"catalogo_{tabla}.csv", "w", encoding="utf-8-sig", newline="") as f:
                w = csv.writer(f)
                w.writerow(["nombre", "veces_usado", "pendiente_revision"])
                pend = dict(self.db.execute(f"SELECT nombre, pendiente_revision FROM {tabla}").fetchall())
                for nombre, veces in sorted(self.uso[tabla].items(), key=lambda x: (-x[1], x[0])):
                    w.writerow([nombre, veces, pend.get(nombre, 0)])
        for tabla in ("genero", "tematica", "aviso"):
            grupos = {}
            for (nombre,) in self.db.execute(f"SELECT nombre FROM {tabla}"):
                grupos.setdefault(clave_similar(nombre), []).append(nombre)
            with open(self.informes / f"posibles_duplicados_{tabla}.csv", "w", encoding="utf-8-sig", newline="") as f:
                w = csv.writer(f)
                w.writerow(["variantes_parecidas", "veces_usado_cada_una"])
                for variantes in grupos.values():
                    if len(variantes) > 1:
                        w.writerow([" | ".join(variantes), " | ".join(str(self.uso[tabla][v]) for v in variantes)])
        priv = RAIZ / "data" / "privado"
        priv.mkdir(parents=True, exist_ok=True)
        with open(priv / "revisoras.csv", "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["alias", "correo"])
            for correo, alias in self.alias.items():
                w.writerow([alias, correo])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("excel")
    ap.add_argument("--db", default=str(RAIZ / "safoteca.db"))
    ap.add_argument("--forzar", action="store_true", help="borra la base de datos existente y la recrea")
    ap.add_argument("--publicar-revisadas", action="store_true",
                    help="pasa a 'publicada' las películas y series revisadas que cumplan los mínimos")
    a = ap.parse_args()

    dbp = Path(a.db)
    fechas_publicacion = {}  # se conservan al recrear la base de datos (para ordenar «Novedades»)
    if dbp.exists():
        if not a.forzar:
            sys.exit(f"{dbp} ya existe. Usa --forzar para recrearla (se perderán los cambios hechos en ella).")
        try:
            old = sqlite3.connect(dbp)
            asegurar_esquema(old)
            for tipo, titulo, anio, fecha in old.execute(
                    "SELECT tipo, lower(titulo_original), anio, publicada_el FROM obra WHERE publicada_el IS NOT NULL"):
                fechas_publicacion[(tipo, titulo, anio)] = fecha
            old.close()
        except sqlite3.Error:
            pass
        dbp.unlink()

    wb = openpyxl.load_workbook(a.excel, data_only=True, read_only=True)
    db = sqlite3.connect(dbp)
    db.executescript((RAIZ / "db" / "schema.sql").read_text(encoding="utf-8"))
    imp = Importador(db, RAIZ / "informes")
    imp.leer_tags(wb)
    imp.leer_generos(wb)

    hojas = {w.title.strip(): w for w in wb.worksheets}
    resumen = {}
    resumen["películas y series"] = imp.hoja_datos(hojas["Datos"])
    if "Copia de Hoja Libros" in hojas:
        resumen["libros"] = imp.hoja_libros(hojas["Copia de Hoja Libros"])
    if "Copia de Hoja Cómics" in hojas:
        resumen["cómics"] = imp.hoja_comics(hojas["Copia de Hoja Cómics"])

    publicadas = 0
    if a.publicar_revisadas:
        for oid, titulo in db.execute(
                "SELECT id, titulo_original FROM obra WHERE estado='revisada' AND tipo IN ('pelicula','serie')").fetchall():
            try:
                db.execute("UPDATE obra SET estado='publicada' WHERE id=?", (oid,))
                publicadas += 1
            except sqlite3.IntegrityError as e:
                imp.inc("Datos", "", titulo, "estado", "revisada", f"no se publica: {e}")
    for (tipo, titulo, anio), fecha in fechas_publicacion.items():
        db.execute("UPDATE obra SET publicada_el = ? WHERE estado = 'publicada' AND tipo = ? "
                   "AND lower(titulo_original) = ? AND anio IS ?", (fecha, tipo, titulo, anio))
    imp.unificar_mayusculas()
    db.commit()
    imp.escribir_informes()
    if imp.letterboxd:
        ruta = RAIZ / "data" / "letterboxd.csv"
        with open(ruta, "w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["id", "titulo", "url"])
            for oid in sorted(imp.letterboxd):
                w.writerow([oid, *imp.letterboxd[oid]])
        print(f"  Letterboxd: {len(imp.letterboxd)} enlaces -> data/letterboxd.csv")

    print("\n=== Importación terminada ===")
    for k, v in resumen.items():
        print(f"  {k}: {v}")
    cont = dict(db.execute("SELECT estado, COUNT(*) FROM obra GROUP BY estado").fetchall())
    print("  estados:", cont, "| publicadas ahora:", publicadas)
    for t in ("genero", "tematica", "aviso", "persona", "obra_enlace"):
        print(f"  {t}: {db.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]}")
    print(f"  incidencias a revisar: {len(imp.incidencias)}  ->  informes/incidencias.csv")
    pend = {t: db.execute(f"SELECT COUNT(*) FROM {t} WHERE pendiente_revision=1").fetchone()[0] for t in ("genero",)}
    print("  géneros fuera del catálogo oficial:", pend["genero"])
    db.close()


if __name__ == "__main__":
    main()
