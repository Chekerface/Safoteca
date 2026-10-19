-- La Safoteca · esquema de base de datos (SQLite)
-- SQL estándar: se puede migrar a PostgreSQL cambiando pocos detalles
-- (INTEGER PRIMARY KEY -> GENERATED ... AS IDENTITY, datetime('now') -> now()).

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS obra (
    id                  INTEGER PRIMARY KEY,
    tipo                TEXT NOT NULL CHECK (tipo IN ('pelicula','serie','libro','comic')),
    titulo_es           TEXT,
    titulo_latam        TEXT,
    titulo_original     TEXT NOT NULL,
    pais                TEXT,
    anio                INTEGER CHECK (anio IS NULL OR anio BETWEEN 1890 AND 2100),
    anio_fin            INTEGER CHECK (anio_fin IS NULL OR (anio_fin BETWEEN 1890 AND 2100 AND anio_fin >= anio)),
    sinopsis            TEXT,
    edad_recomendada    TEXT CHECK (edad_recomendada IS NULL OR edad_recomendada = 'TP'
                                    OR (edad_recomendada GLOB '[0-9]*' AND CAST(edad_recomendada AS INTEGER) BETWEEN 0 AND 18)),
    nivel_relevancia    TEXT CHECK (nivel_relevancia IS NULL OR nivel_relevancia IN ('A','B','C')),
    temporada_aparicion TEXT,
    coleccion           TEXT,            -- saga / colección (libros y cómics)
    editorial           TEXT,            -- libros y cómics
    volumenes           TEXT,            -- libros y cómics
    disponible_espana   INTEGER CHECK (disponible_espana IS NULL OR disponible_espana IN (0,1)),
    final_feliz         INTEGER CHECK (final_feliz IS NULL OR final_feliz IN (0,1)),
    poster_origen       TEXT,            -- URL de donde se obtuvo la imagen
    poster_archivo      TEXT,            -- nombre base del archivo alojado (sin extensión)
    estado              TEXT NOT NULL DEFAULT 'borrador'
                        CHECK (estado IN ('borrador','revisada','publicada')),
    revisora_alias      TEXT,            -- alias, nunca el correo
    notas_internas      TEXT,
    creada_el           TEXT NOT NULL DEFAULT (datetime('now')),
    actualizada_el      TEXT NOT NULL DEFAULT (datetime('now')),
    publicada_el        TEXT             -- cuándo pasó a 'publicada' (UTC); se rellena sola con un trigger
);

CREATE INDEX IF NOT EXISTS idx_obra_estado_tipo ON obra (estado, tipo);

-- Catálogos ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS genero (
    id INTEGER PRIMARY KEY,
    nombre TEXT NOT NULL UNIQUE COLLATE NOCASE,
    pendiente_revision INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS tematica (
    id INTEGER PRIMARY KEY,
    nombre TEXT NOT NULL UNIQUE COLLATE NOCASE,
    pendiente_revision INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS aviso (
    id INTEGER PRIMARY KEY,
    nombre TEXT NOT NULL UNIQUE COLLATE NOCASE,
    es_tw INTEGER CHECK (es_tw IS NULL OR es_tw IN (0,1)),
    categoria TEXT,                       -- violencia, discriminación, muerte de personajes LGBT+...
    descripcion TEXT,
    pendiente_revision INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS obra_genero   (obra_id INTEGER NOT NULL REFERENCES obra(id) ON DELETE CASCADE,
                                          genero_id INTEGER NOT NULL REFERENCES genero(id),
                                          PRIMARY KEY (obra_id, genero_id));
CREATE TABLE IF NOT EXISTS obra_tematica (obra_id INTEGER NOT NULL REFERENCES obra(id) ON DELETE CASCADE,
                                          tematica_id INTEGER NOT NULL REFERENCES tematica(id),
                                          PRIMARY KEY (obra_id, tematica_id));
CREATE TABLE IF NOT EXISTS obra_aviso    (obra_id INTEGER NOT NULL REFERENCES obra(id) ON DELETE CASCADE,
                                          aviso_id INTEGER NOT NULL REFERENCES aviso(id),
                                          PRIMARY KEY (obra_id, aviso_id));

-- Grupos de etiquetas ----------------------------------------------------
-- Un subgrupo (hijo) pertenece a un grupo (padre): Racismo -> Discriminación -> Violencia.
-- Cuando una obra recibe un hijo (por el formulario, un Excel o a mano) recibe sola todos sus grupos
-- (los directos y los de más arriba). Las vistas *_ancestro calculan esa cadena completa.
CREATE TABLE IF NOT EXISTS tematica_grupo (hijo_id INTEGER NOT NULL REFERENCES tematica(id) ON DELETE CASCADE,
                                           padre_id INTEGER NOT NULL REFERENCES tematica(id) ON DELETE CASCADE,
                                           PRIMARY KEY (hijo_id, padre_id), CHECK (hijo_id <> padre_id));
CREATE TABLE IF NOT EXISTS aviso_grupo    (hijo_id INTEGER NOT NULL REFERENCES aviso(id) ON DELETE CASCADE,
                                           padre_id INTEGER NOT NULL REFERENCES aviso(id) ON DELETE CASCADE,
                                           PRIMARY KEY (hijo_id, padre_id), CHECK (hijo_id <> padre_id));

CREATE VIEW IF NOT EXISTS tematica_ancestro AS
    WITH RECURSIVE a(hijo_id, padre_id) AS (
        SELECT hijo_id, padre_id FROM tematica_grupo
        UNION SELECT a.hijo_id, g.padre_id FROM a JOIN tematica_grupo g ON g.hijo_id = a.padre_id)
    SELECT hijo_id, padre_id FROM a WHERE hijo_id <> padre_id;
CREATE VIEW IF NOT EXISTS aviso_ancestro AS
    WITH RECURSIVE a(hijo_id, padre_id) AS (
        SELECT hijo_id, padre_id FROM aviso_grupo
        UNION SELECT a.hijo_id, g.padre_id FROM a JOIN aviso_grupo g ON g.hijo_id = a.padre_id)
    SELECT hijo_id, padre_id FROM a WHERE hijo_id <> padre_id;

CREATE TRIGGER IF NOT EXISTS obra_tematica_grupos AFTER INSERT ON obra_tematica
BEGIN
    INSERT OR IGNORE INTO obra_tematica(obra_id, tematica_id)
        SELECT NEW.obra_id, padre_id FROM tematica_ancestro WHERE hijo_id = NEW.tematica_id;
END;
CREATE TRIGGER IF NOT EXISTS obra_aviso_grupos AFTER INSERT ON obra_aviso
BEGIN
    INSERT OR IGNORE INTO obra_aviso(obra_id, aviso_id)
        SELECT NEW.obra_id, padre_id FROM aviso_ancestro WHERE hijo_id = NEW.aviso_id;
END;
-- Si se crea un grupo nuevo, las obras que ya tenían el subgrupo lo reciben también.
CREATE TRIGGER IF NOT EXISTS tematica_grupo_nuevo AFTER INSERT ON tematica_grupo
BEGIN
    INSERT OR IGNORE INTO obra_tematica(obra_id, tematica_id)
        SELECT obra_id, NEW.padre_id FROM obra_tematica WHERE tematica_id = NEW.hijo_id;
END;
CREATE TRIGGER IF NOT EXISTS aviso_grupo_nuevo AFTER INSERT ON aviso_grupo
BEGIN
    INSERT OR IGNORE INTO obra_aviso(obra_id, aviso_id)
        SELECT obra_id, NEW.padre_id FROM obra_aviso WHERE aviso_id = NEW.hijo_id;
END;

-- Personas y enlaces -----------------------------------------------------
CREATE TABLE IF NOT EXISTS persona (
    id INTEGER PRIMARY KEY,
    nombre TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS obra_persona (
    obra_id INTEGER NOT NULL REFERENCES obra(id) ON DELETE CASCADE,
    persona_id INTEGER NOT NULL REFERENCES persona(id),
    rol TEXT NOT NULL CHECK (rol IN ('actriz','director','autore','guionista','dibujante','entintador','colorista')),
    PRIMARY KEY (obra_id, persona_id, rol)
);
CREATE TABLE IF NOT EXISTS obra_enlace (
    id INTEGER PRIMARY KEY,
    obra_id INTEGER NOT NULL REFERENCES obra(id) ON DELETE CASCADE,
    tipo TEXT NOT NULL CHECK (tipo IN ('donde_ver','info')),
    url TEXT NOT NULL
);

-- Validaciones (equivalente a lo que harías en PL/SQL) -----------------------
-- Una obra solo puede publicarse si tiene lo mínimo necesario.
CREATE TRIGGER IF NOT EXISTS obra_validar_publicacion_upd
BEFORE UPDATE OF estado ON obra
WHEN NEW.estado = 'publicada'
 AND (NEW.nivel_relevancia IS NULL OR NEW.sinopsis IS NULL OR trim(NEW.sinopsis) = '')
BEGIN
    SELECT RAISE(ABORT, 'No se puede publicar: falta nivel de relevancia o sinopsis');
END;

CREATE TRIGGER IF NOT EXISTS obra_validar_publicacion_ins
BEFORE INSERT ON obra
WHEN NEW.estado = 'publicada'
 AND (NEW.nivel_relevancia IS NULL OR NEW.sinopsis IS NULL OR trim(NEW.sinopsis) = '')
BEGIN
    SELECT RAISE(ABORT, 'No se puede publicar: falta nivel de relevancia o sinopsis');
END;

CREATE TRIGGER IF NOT EXISTS obra_touch
AFTER UPDATE ON obra
FOR EACH ROW
WHEN NEW.actualizada_el = OLD.actualizada_el
BEGIN
    UPDATE obra SET actualizada_el = datetime('now') WHERE id = NEW.id;
END;

-- Fecha de publicación: se anota sola la primera vez que una obra pasa a 'publicada'.
CREATE TRIGGER IF NOT EXISTS obra_fecha_publicacion_upd
AFTER UPDATE OF estado ON obra
WHEN NEW.estado = 'publicada' AND OLD.estado <> 'publicada'
BEGIN
    UPDATE obra SET publicada_el = datetime('now') WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS obra_fecha_publicacion_ins
AFTER INSERT ON obra
WHEN NEW.estado = 'publicada' AND NEW.publicada_el IS NULL
BEGIN
    UPDATE obra SET publicada_el = datetime('now') WHERE id = NEW.id;
END;

-- Lo único que sale a producción: películas y series publicadas ----------------
CREATE VIEW IF NOT EXISTS vista_publicable AS
SELECT * FROM obra
WHERE estado = 'publicada' AND tipo IN ('pelicula','serie');
