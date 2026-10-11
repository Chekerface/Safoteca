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

## 4b. Añadir o completar obras con la plantilla
La plantilla `Plantilla_La_Safoteca.xlsx` (hoja «Obras») es la forma de subir obras nuevas o completar las pendientes. Una fila por obra, con desplegables.
```bash
python tools/importar_plantilla.py Plantilla_rellena.xlsx --simular   # solo informa de lo que pasaría
python tools/importar_plantilla.py Plantilla_rellena.xlsx             # guarda, regenera web/data y hace copia de la BD
```
- **Id con valor** = actualiza esa obra. **Id vacío** = busca por tipo + título original (+ año); si existe, la actualiza; si no, crea una nueva.
- Una casilla vacía **no borra** lo que ya hay. Géneros, temáticas, avisos, actrices, directore y enlaces se sustituyen enteros solo si la fila trae algo.
- **Revisada = Sí** publica la obra (película o serie) si tiene sinopsis y nivel; si no, avisa y queda como «revisada». Desde la plantilla nunca se despublica nada.
- Temáticas, avisos o géneros nuevos se crean como «pendiente de revisión».
- La columna «Letterboxd (enlace)» se guarda en `data/letterboxd.csv` (y el botón sale en la ficha).
- Las incidencias salen por pantalla y en `informes/incidencias_plantilla.csv`. Las copias de la BD quedan en `data/privado/copias/`.
- Después: `git add -A`, commit y subir. Si hay pósters nuevos, Actions → «Descargar pósters».

## 5. Editar mientras no exista el panel
Instalad **DB Browser for SQLite** (gratuito). Abre `safoteca.db`. Para publicar una obra:
```sql
UPDATE obra SET estado = 'publicada' WHERE id = 123;
```
Si falta la sinopsis o el nivel de relevancia, la base de datos lo rechaza con un mensaje claro.
Antes de editar, haced copia de `safoteca.db`. Solo una persona a la vez debe tenerla abierta (con una editora a la vez es suficiente; el panel de edición para varias a la vez queda para más adelante). La lista de pendientes (sinopsis, nivel, etc.) se lleva en un Excel aparte que no se sube al repositorio; cuando esté rellena se aplica con `tools/importar_plantilla.py` (ver 4b).

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

## 8. La web
La web está en `web/` y no necesita instalar nada: son archivos estáticos que leen `web/data/*.json`.

**Verla en tu ordenador** (desde la carpeta del proyecto):
```bash
python -m http.server -d web 8000
```
y abre http://localhost:8000. Para probarla en el móvil, usa la dirección de tu ordenador en la red local.

**Qué hace:**
- **Inicio:** Novedades (las más recientes), Películas imprescindibles y Series imprescindibles (nivel A).
- **Series y películas:** búsqueda por título o actriz (sin distinguir tildes), filtros por tipo, nivel, género, temática y edad máxima.
- **Ficha:** los avisos de contenido están ocultos hasta que la persona los pide. En Ajustes puede mostrarlos siempre.
- **Qué prefiero evitar:** la persona elige avisos y las obras que los tienen desaparecen de todas las listas, sin decir cuáles son.
  Evitar un aviso ignora mayúsculas, tildes y puntuación, así que "Sindrome de la lesbiana muerta." cuenta como
  "Síndrome de la lesbiana muerta". Las etiquetas se muestran siempre tal cual están en la base de datos.
- **Favoritos y preferencias:** se guardan solo en el dispositivo (sin cuentas ni servidor).
- **Sin conexión:** se puede instalar en el móvil y funciona sin internet tras la primera visita.

**Personalizar sin tocar código** (`web/config.js`): el lema y la explicación de los niveles A, B y C. Mientras esa
explicación esté vacía, no se muestra nada.

**Logo y tipografías:** el logotipo y el búholira están en `web/marca/` (versiones clara y oscura, tal como los
diseñasteis). Los iconos de la app (`web/icons/`) se generan con el búholira en blanco sobre el lila `#9c88bb`:
`python tools/generar_iconos.py`. La tipografía del logotipo (Bicycle) va dentro del propio SVG; el resto de la web usa
tipografías del dispositivo (sin descargas). Si queréis tipografías propias, añadid los archivos `.woff2` a
`web/fonts/` y declaradlas con `@font-face` en `web/css/estilos.css`.

## 9. Publicar y actualizar la web
**Primera vez:** en GitHub, *Settings → Pages → Build and deployment → Source: GitHub Actions*. A partir de ahí, cada
cambio en `web/` que llegue a `main` se publica solo (pestaña *Actions* para ver el progreso). La dirección será
`https://chekerface.github.io/Safoteca/`.

**Pósters sin usar Python en tu ordenador:** en GitHub, pestaña *Actions → Descargar pósters → Run workflow*.
GitHub descarga las imágenes de `data/posters.csv`, las optimiza, las guarda en `web/img/` y vuelve a publicar la web.
El resultado (qué enlaces han fallado) queda en `data/posters_informe.csv`. Para un póster que falla, subid la imagen
a `web/img/originales/<id>.jpg` y lanzad el botón otra vez. `data/posters.csv` se regenera con `tools/exportar_json.py`.

**Cada vez que cambiéis datos** (con la base de datos ya como fuente de verdad):
```bash
python tools/descargar_imagenes.py      # solo si hay obras nuevas
python tools/exportar_json.py
git checkout -b actualizar-datos
git add web
git commit -m "Actualizar catálogo"
git push -u origin actualizar-datos     # y abrid el PR en GitHub
```
Al fusionar el PR, la web se actualiza. Quien ya la tenga abierta verá los datos nuevos la siguiente vez que la abra con conexión.
