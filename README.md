# La Safoteca

Catálogo sin ánimo de lucro de series y películas (y, más adelante, libros y cómics) con representación
lésbica y bisexual, con información sobre la calidad de la representación y avisos de contenido.

## Arquitectura

```
Excel de Glide (una sola vez) → importar_excel.py → safoteca.db (SQLite)
                                                        │
                       descargar_imagenes.py ───────────┤  (pósters → WebP en web/img)
                                                        │
                                    exportar_json.py ───┘  (solo películas y series publicadas)
                                                        ↓
                                  web/ (estática) → GitHub Pages
```

- **Base de datos:** SQLite (un archivo). Sin servidor, sin puertos abiertos. **No está en este repositorio:** vive en el
  repositorio privado `Chekerface/Safoteca-datos` (con sus copias de seguridad), que se clona al lado de este. Los
  scripts de `tools/` la encuentran solos (ver `tools/rutas.py`). Después de cada cambio hay que subirla allí.
- **Producción:** solo salen películas y series con estado `publicada`. Libros y cómics quedan en la base de datos.
- **Estados:** `borrador` → `revisada` → `publicada`. Un disparador impide publicar sin sinopsis o nivel de relevancia.
- **Privacidad:** las revisoras se guardan con alias (R01, R02…); los correos solo existen en el repositorio privado de datos.

## Estructura

| Carpeta | Contenido |
|---|---|
| `db/schema.sql` | Tablas, validaciones y la vista `vista_publicable` |
| `tools/` | Scripts de importación, imágenes y exportación |
| `data/mapeos/` | CSV editables para unificar géneros, temáticas y avisos |
| `data/privado/` | **No se sube a GitHub.** Excel de trabajo temporales (la base de datos y las copias van en `Safoteca-datos`) |
| `informes/` | Resultados de cada ejecución (qué hay que revisar) |
| `web/` | La web (PWA estática): código, datos e imágenes generados |
| `.github/workflows/` | Publicación automática en GitHub Pages |
| `docs/guia.md` | Guía paso a paso |

La web incluye búsqueda, filtros, favoritos, avisos de contenido ocultables y una opción para evitar avisos concretos.

Empieza por [`docs/guia.md`](docs/guia.md).
