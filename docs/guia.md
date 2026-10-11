# Guía paso a paso

## 0. Qué necesitas
- **Python 3.10 o superior** en tu ordenador (no en el Synology). Descarga: python.org.
- Este proyecto descargado.
- El Excel `Base_de_datos.xlsx` guardado en `data/privado/` (esa carpeta nunca se sube a GitHub).

Abre una terminal en la carpeta del proyecto y ejecuta, una sola vez:

```bash
python -m venv .venv
# Windows:   .venv\Scripts\activate
# Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

## 1. Importar el Excel
```bash
python tools/importar_excel.py data/privado/Base_de_datos.xlsx
```
Crea `safoteca.db` y la carpeta `informes/`. Si la base de datos ya existe, el script se detiene para no
borrar trabajo: usa `--forzar` solo cuando quieras empezar de cero.

Para publicar de golpe las películas y series que ya estaban marcadas como revisadas en Glide:
```bash
python tools/importar_excel.py data/privado/Base_de_datos.xlsx --forzar --publicar-revisadas
```

## 2. Revisar los informes (`informes/`)
| Archivo | Qué hacer |
|---|---|
| `incidencias.csv` | Lista de datos dudosos con hoja y número de fila del Excel. Corregid en el Excel y reimportad (con `--forzar`) mientras la base de datos sea una copia. |
| `catalogo_genero.csv`, `catalogo_tematica.csv`, `catalogo_aviso.csv` | Cada etiqueta con su número de usos. |
| `posibles_duplicados_*.csv` | Etiquetas casi iguales (por tildes, plural...). |

**Temporadas en el título:** es intencionado. Cada temporada (o grupo de temporadas) con elenco o historia distintos
se cataloga como entrada propia, con su nivel de relevancia, por ejemplo "Skins (Temporadas 3 y 4)". El importador
no lo trata como un problema. Solo avisa de títulos **idénticos** repetidos.

**Unificar etiquetas:** añadid filas a `data/mapeos/generos.csv`, `tematicas.csv` o `avisos.csv`:
```
variante,canonico
Thriler,Thriller
```
Si `canonico` queda vacío, la etiqueta se **elimina**. Después reimportad con `--forzar`.

**Avisos de contenido:** se mantienen tal cual están en el Excel, con todo su detalle ("Violación", "Acoso sexual",
"Síndrome de la lesbiana muerta"...), porque cada persona debe poder saber con precisión qué va a encontrar.
No se agrupan en categorías ni se fusionan. La única excepción técnica es que dos avisos que solo se diferencian en
mayúsculas o minúsculas ("Asesinato" y "asesinato") cuentan como el mismo, para que el filtro no los muestre duplicados.
Los avisos que se parecen pero no son idénticos ("Asesinato" y "Asesinatos") se conservan por separado.

**Géneros:** se aplican solo las unificaciones que el equipo ha aprobado (`data/mapeos/generos.csv`). El resto de
valores se mantiene como en el Excel. Las decisiones están anotadas en `data/mapeos/propuestas_a_decidir.csv`.

## 3. Imágenes
```bash
python tools/descargar_imagenes.py --pausa 1
```
Descarga cada póster, guarda el original en `originales/` y crea dos versiones WebP en `web/img/`.
Se puede interrumpir y repetir. Mira `informes/imagenes.csv`:

| Estado | Significado |
|---|---|
| `ok` | Listo |
| `enlace_roto` | El enlace ya no existe |
| `no_es_imagen` | El enlace devuelve otra cosa (página web, imagen minúscula) |
| `sin_imagen` | La obra nunca tuvo póster |

Para las que fallan: guardad la imagen como `originales/<id>.jpg` (el `id` está en el informe) y volved a ejecutar
el script. Detecta el archivo y lo procesa sin descargar nada.

> Los pósters tienen derechos de autor. Subir copias de baja resolución para un catálogo no lucrativo es
> habitual, pero no está exento de riesgo. Guardamos `poster_origen` para saber de dónde viene cada una.

## 4. Exportar para la web
```bash
python tools/exportar_json.py
```
Genera `web/data/obras.json` y `web/data/catalogos.json` solo con películas y series **publicadas**.
No salen ni los estados, ni los alias, ni los correos.

## 5. Editar mientras no exista el panel
Instalad **DB Browser for SQLite** (gratuito). Abre `safoteca.db`. Para publicar una obra:
```sql
UPDATE obra SET estado = 'publicada' WHERE id = 123;
```
Si falta la sinopsis o el nivel de relevancia, la base de datos lo rechaza con un mensaje claro.
Antes de editar, haced copia de `safoteca.db`. Solo una persona a la vez debe tenerla abierta.

## 6. Tu Synology DS114
- Es un modelo de 2014 con procesador ARM y 512 MB de RAM, y DSM 7.1.1 es su última versión. Lo más probable es que no admita Docker
  (comprobadlo en el Centro de paquetes: si no aparece Container Manager, no lo tiene). Por eso este diseño **no depende del NAS**.
- Úsalo como **almacén de copias de seguridad**: copia periódicamente `safoteca.db` y la carpeta `originales/` a una
  carpeta compartida (o con Hyper Backup, si está disponible en tu modelo).
- No abráis puertos del router hacia el NAS: la web pública va en GitHub Pages y no lo necesita.

## 7. Subir a GitHub
`.gitignore` ya excluye `data/privado/`, `*.xlsx`, `*.db` y `originales/`. Antes de subir, comprueba que **no** aparece
el Excel ni `revisoras.csv` (contienen correos) en la lista de archivos. El repositorio público debe contener solo
código, `data/mapeos/` y `web/`.

## Pendiente (siguientes pasos)
1. Web PWA (pantallas de inicio, listado, favoritos, ficha y filtros) que lea `web/data/*.json`.
2. Panel de edición para el equipo (en vez de DB Browser).
3. Despliegue en GitHub Pages.
