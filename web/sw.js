// Service worker: la web funciona sin conexión y se actualiza sola cuando hay red.
const CACHE_APP = "safoteca-app-v19";
const CACHE_IMG = "safoteca-img";
const ACTUALES = [CACHE_APP, CACHE_IMG];
const PRECARGA = [
  "./", "./index.html", "./css/estilos.css", "./css/temas.css", "./js/app.js", "./js/temas.js", "./config.js",
  "./manifest.webmanifest", "./marca/buholira.svg", "./marca/logo-horizontal.svg", "./marca/logo-horizontal-oscuro.svg", "./marca/logo-vertical.svg", "./marca/logo-vertical-oscuro.svg", "./icons/icon-192.png", "./icons/icon-512.png",
  "./data/obras.json", "./data/catalogos.json"
];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE_APP).then((c) => c.addAll(PRECARGA)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys()
      .then((claves) => Promise.all(claves.filter((k) => !ACTUALES.includes(k)).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

// Copia guardada al instante y actualización por detrás: la web abre rápido aunque la red sea lenta.
// Lo nuevo se ve en la visita siguiente (o al recargar). Si no hay copia, se espera a la red.
async function copiaYActualiza(req, cacheName) {
  const cache = await caches.open(cacheName);
  const guardada = await cache.match(req, { ignoreSearch: true });
  const red = fetch(req).then((res) => { if (res.ok) cache.put(req, res.clone()); return res; });
  if (guardada) { red.catch(() => {}); return guardada; }
  try { return await red; }
  catch (err) {
    if (req.mode === "navigate") { const inicio = await cache.match("./index.html"); if (inicio) return inicio; }
    throw err;
  }
}

async function primeroCache(req) {
  const cache = await caches.open(CACHE_IMG);
  const guardada = await cache.match(req);
  if (guardada) return guardada;
  const res = await fetch(req);
  if (res.ok) cache.put(req, res.clone());
  return res;
}

self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;
  if (url.pathname.includes("/img/")) e.respondWith(primeroCache(req));
  else e.respondWith(copiaYActualiza(req, CACHE_APP));
});
