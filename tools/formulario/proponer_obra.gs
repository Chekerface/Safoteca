/**
 * La Safoteca · servicio de «Proponer una obra» (la pantalla #/proponer de la web)
 *
 * Hace dos cosas, sin coste:
 *   1. Busca en TMDB (The Movie Database) para rellenar solos los datos de una serie o película.
 *      La clave de TMDB se guarda aquí, no en la web, así nadie puede copiarla del código público.
 *   2. Recibe las propuestas, comprueba que vienen de una cuenta de Google y las añade como una fila
 *      más de la hoja de respuestas del formulario (mismas columnas), así que el importador no cambia.
 *
 * Instalación (una sola vez): ver los pasos en el chat o en la Retrospectiva técnica (componente E6).
 *   - Se pega en la hoja de RESPUESTAS del formulario: Extensiones → Apps Script.
 *   - Propiedades del script (Configuración del proyecto): TMDB_TOKEN y CLIENT_ID.
 *   - Implementar → Nueva implementación → Aplicación web · Ejecutar como: Yo · Acceso: Cualquier usuario.
 */
const MAX_POR_DIA = 15;            // propuestas por cuenta y día (protección contra abusos)
const CACHE_SEG = 6 * 60 * 60;     // las respuestas de TMDB se guardan 6 horas

/* ===================== GET: búsquedas en TMDB ===================== */
function doGet(e) {
  const p = (e && e.parameter) || {};
  try {
    if (p.accion === "buscar") return json(buscar(p.q || ""));
    if (p.accion === "enlace") return json(porEnlace(p.url || ""));
    if (p.accion === "detalle") return json(detalle(p.tipo, p.id));
    return json({ ok: true, servicio: "La Safoteca · proponer obra" });
  } catch (err) {
    return json({ error: String((err && err.message) || err) });
  }
}

function json(o) {
  return ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON);
}

function tmdb(ruta, params) {
  const clave = PropertiesService.getScriptProperties().getProperty("TMDB_TOKEN");
  if (!clave) throw new Error("Falta la propiedad TMDB_TOKEN");
  const todos = Object.assign({ language: "es-ES" }, params || {});
  const cabeceras = { accept: "application/json" };
  if (clave.length > 60) cabeceras.Authorization = "Bearer " + clave;   // token de lectura (v4)
  else todos.api_key = clave;                                           // clave corta (v3)
  const qs = Object.keys(todos).map(k => k + "=" + encodeURIComponent(todos[k])).join("&");
  const url = "https://api.themoviedb.org/3" + ruta + "?" + qs;
  const cache = CacheService.getScriptCache();
  const k = Utilities.base64EncodeWebSafe(Utilities.computeDigest(Utilities.DigestAlgorithm.MD5, ruta + "?" + qs.replace(/api_key=[^&]*/, "")));
  const guardado = cache.get(k);
  if (guardado) return JSON.parse(guardado);
  const r = UrlFetchApp.fetch(url, { headers: cabeceras, muteHttpExceptions: true });
  if (r.getResponseCode() !== 200) throw new Error("TMDB respondió " + r.getResponseCode());
  const txt = r.getContentText();
  if (txt.length < 95000) cache.put(k, txt, CACHE_SEG);
  return JSON.parse(txt);
}

const anioDe = f => (f && /^\d{4}/.test(f)) ? parseInt(f.slice(0, 4), 10) : null;
const posterDe = (ruta, ancho) => ruta ? "https://image.tmdb.org/t/p/" + (ancho || "w342") + ruta : "";

function buscar(q) {
  q = String(q).trim().slice(0, 120);
  if (q.length < 2) return { resultados: [] };
  const d = tmdb("/search/multi", { query: q, include_adult: "false" });
  const resultados = (d.results || [])
    .filter(x => x.media_type === "movie" || x.media_type === "tv")
    .slice(0, 10)
    .map(x => ({
      tipo: x.media_type === "tv" ? "serie" : "pelicula",
      id: x.id,
      titulo: x.title || x.name || "",
      original: x.original_title || x.original_name || "",
      anio: anioDe(x.release_date || x.first_air_date),
      poster: posterDe(x.poster_path, "w154"),
    }));
  return { resultados };
}

function porEnlace(url) {
  url = String(url).trim();
  let m = url.match(/themoviedb\.org\/(movie|tv)\/(\d+)/i);
  if (m) return detalle(m[1] === "tv" ? "serie" : "pelicula", m[2]);
  m = url.match(/\b(tt\d{5,10})\b/i);
  if (m) {
    const d = tmdb("/find/" + m[1].toLowerCase(), { external_source: "imdb_id" });
    if (d.movie_results && d.movie_results.length) return detalle("pelicula", d.movie_results[0].id);
    if (d.tv_results && d.tv_results.length) return detalle("serie", d.tv_results[0].id);
    return { error: "No encuentro esa obra en TMDB a partir del enlace de IMDb. Prueba a buscarla por el título." };
  }
  if (/letterboxd\.com/i.test(url)) return { error: "letterboxd" };
  return { error: "Ese enlace no es de IMDb ni de TMDB. Prueba a buscar por el título." };
}

function detalle(tipo, id) {
  id = String(id).replace(/\D/g, "");
  if (!id) throw new Error("Falta el identificador");
  const serie = tipo === "serie";
  const d = tmdb((serie ? "/tv/" : "/movie/") + id, { append_to_response: "credits,external_ids,watch/providers" });
  const reparto = ((d.credits && d.credits.cast) || []);
  const actrices = reparto.filter(p => p.gender === 1).slice(0, 6).map(p => p.name);
  const equipo = ((d.credits && d.credits.crew) || []);
  let direccion = serie ? (d.created_by || []).map(p => p.name) : [];
  if (!direccion.length) direccion = equipo.filter(p => p.job === "Director").map(p => p.name);
  const paises = serie ? (d.origin_country || []) : (d.production_countries || []).map(c => c.iso_3166_1);
  const prov = (d["watch/providers"] && d["watch/providers"].results && d["watch/providers"].results.ES) || {};
  const plataformas = [];
  ["flatrate", "free", "ads"].forEach(k => (prov[k] || []).forEach(p => { if (plataformas.indexOf(p.provider_name) < 0) plataformas.push(p.provider_name); }));
  const imdb = d.external_ids && d.external_ids.imdb_id;
  const terminada = serie && /Ended|Canceled/i.test(d.status || "");
  return {
    tipo: serie ? "serie" : "pelicula",
    tmdb: id,
    titulo: d.title || d.name || "",
    original: d.original_title || d.original_name || "",
    anio: anioDe(d.release_date || d.first_air_date),
    anio_fin: terminada ? anioDe(d.last_air_date) : null,
    temporadas: serie ? (d.number_of_seasons || null) : null,
    paises: paises.slice(0, 3),
    sinopsis: d.overview || "",
    generos: (d.genres || []).map(g => g.name),
    direccion: direccion.slice(0, 4),
    actrices: actrices,
    plataformas_es: plataformas,
    poster: posterDe(d.poster_path, "w780"),
    info: imdb ? "https://www.imdb.com/title/" + imdb + "/" : "https://www.themoviedb.org/" + (serie ? "tv/" : "movie/") + id,
    letterboxd: serie ? "" : "https://letterboxd.com/tmdb/" + id + "/",
  };
}

/* ===================== POST: recibir una propuesta ===================== */
function doPost(e) {
  const lock = LockService.getScriptLock();
  try {
    const cuerpo = JSON.parse((e && e.postData && e.postData.contents) || "{}");
    if (cuerpo.web) return json({ ok: true });                   // casilla trampa rellena: es un robot
    const email = cuentaGoogle(cuerpo.credencial);
    if (!email) return json({ error: "No se ha podido comprobar tu cuenta de Google. Vuelve a entrar." });
    const d = cuerpo.datos || {};
    if (!limpio(d["Título original"]) || !limpio(d["Tipo"])) return json({ error: "Faltan el tipo o el título original." });

    lock.waitLock(20000);
    const props = PropertiesService.getScriptProperties();
    const hoy = Utilities.formatDate(new Date(), "Europe/Madrid", "yyyyMMdd");
    const kCuenta = "envios_" + hoy + "_" + Utilities.base64EncodeWebSafe(email);
    const n = parseInt(props.getProperty(kCuenta) || "0", 10);
    if (n >= MAX_POR_DIA) return json({ error: "Has enviado muchas propuestas hoy. Vuelve a intentarlo mañana." });

    const hoja = hojaRespuestas();
    const extra = ["Otras temáticas (separadas por comas)", "Otros avisos (separados por comas)", "Origen", "TMDB"];
    let cab = hoja.getRange(1, 1, 1, hoja.getLastColumn()).getValues()[0].map(String);
    extra.forEach(c => { if (cab.map(norm).indexOf(norm(c)) < 0) { hoja.getRange(1, cab.length + 1).setValue(c); cab.push(c); } });

    const valores = Object.assign({}, d, {
      "Origen": "web",
      "TMDB": limpio(cuerpo.tmdb),
    });
    const usadas = {};
    const fila = cab.map(h => {
      const k = norm(h);
      if (k === "timestamp" || k === "marca temporal") return new Date();
      if (k === "email address" || k === "direccion de correo electronico") return email;
      for (const prefijo of ["tematica", "aviso", "genero"]) {
        if (k.indexOf(prefijo) === 0) {                     // la primera columna del grupo lleva todo
          if (usadas[prefijo]) return "";
          usadas[prefijo] = true;
          return limpio(valores[{ tematica: "Temática", aviso: "Aviso", genero: "Género" }[prefijo]]);
        }
      }
      const clave = Object.keys(valores).filter(x => norm(x) === k)[0];
      return clave ? limpio(valores[clave]) : "";
    });
    hoja.appendRow(fila);
    props.setProperty(kCuenta, String(n + 1));
    return json({ ok: true });
  } catch (err) {
    return json({ error: "No se ha podido guardar: " + String((err && err.message) || err) });
  } finally {
    try { lock.releaseLock(); } catch (_) {}
  }
}

/* Comprueba con Google que la credencial (ID token) es buena, es para esta web y tiene el correo verificado. */
function cuentaGoogle(credencial) {
  if (!credencial) return null;
  const cliente = PropertiesService.getScriptProperties().getProperty("CLIENT_ID");
  const r = UrlFetchApp.fetch("https://oauth2.googleapis.com/tokeninfo?id_token=" + encodeURIComponent(credencial), { muteHttpExceptions: true });
  if (r.getResponseCode() !== 200) return null;
  const t = JSON.parse(r.getContentText());
  const emisor = t.iss === "accounts.google.com" || t.iss === "https://accounts.google.com";
  if (!emisor || t.aud !== cliente || String(t.email_verified) !== "true") return null;
  if (parseInt(t.exp, 10) * 1000 < Date.now()) return null;
  return t.email;
}

/* La pestaña de respuestas: la que tiene las columnas «Tipo» y «Título original». */
function hojaRespuestas() {
  const libro = SpreadsheetApp.getActiveSpreadsheet();
  for (const h of libro.getSheets()) {
    if (h.getLastColumn() < 2) continue;
    const cab = h.getRange(1, 1, 1, h.getLastColumn()).getValues()[0].map(norm);
    if (cab.indexOf("tipo") >= 0 && cab.indexOf("titulo original") >= 0) return h;
  }
  throw new Error("No encuentro la pestaña de respuestas (con las columnas Tipo y Título original)");
}

function norm(s) {
  return String(s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().trim();
}
function limpio(v) {
  return String(v == null ? "" : v).trim().slice(0, 5000);
}

/* Para probar desde el editor: Ejecutar → probarTMDB (mira el registro). */
function probarTMDB() {
  console.log(JSON.stringify(buscar("Gap the series")).slice(0, 500));
  console.log(JSON.stringify(porEnlace("https://www.imdb.com/title/tt0115736/")).slice(0, 800));
}
