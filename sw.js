// Service worker del Visor GeoChile.
// OJO: el origen cvenegas-sernageomin.github.io lo comparten varias PWA (Geonotas, catastro...):
// solo se tocan las cachés con prefijo "geochile-", nunca las de las otras apps.
const VER = 'geochile-shell-9';
const DATOS = 'geochile-datos';   // datos/*.json (GDB): caché aparte para que no se pierdan al subir VER
const MAPAS = 'geochile-mapas';   // overlays y leyendas que el usuario abrió: quedan para usarlos sin señal
const SHELL = ['./', 'index.html', 'capas.json', 'viewer_legend.js?v=20260827', 'manifest.json', 'datos.js?v=20261015', 'vendor/leaflet-rotate.js', 'vendor/wmm.js',
  'icons/icono.svg', 'icons/icono-192.png', 'assets/banner_sernageomin.jpg',
  'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css', 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(VER).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks
    .filter(k => k.startsWith('geochile-shell-') && k !== VER).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  const propio = url.origin === location.origin && url.pathname.startsWith(new URL('./', location).pathname);
  if (propio && /\/(overlays|leyendas|peligros|hillshade)\//.test(url.pathname)) {
    e.respondWith(mapa(req, url, MAPAS));
  } else if (propio && /\/datos\/[\w.-]+\.json$/.test(url.pathname)) {
    e.respondWith(mapa(req, url, DATOS));   // caché primero: el ?v= (DATA_V en datos.js) cambia al regenerar
  } else if (propio || url.hostname === 'unpkg.com') {
    // red primero (capas.json e index cambian con cada publicación); sin señal, lo guardado
    e.respondWith(fetch(req).then(r => {
      if (r.ok) { const copia = r.clone(); caches.open(VER).then(c => c.put(req, copia)); }
      return r;
    }).catch(() => caches.match(req, { ignoreSearch: url.pathname.endsWith('/') || url.pathname.endsWith('index.html') })
      .then(r => r || caches.match('index.html'))));
  }
  // teselas del satélite y demás: directo a la red
});

// Overlays y leyendas: caché primero. El ?v= cambia al republicar un mapa; al guardar la
// versión nueva se borra la vieja del mismo archivo para no acumular imágenes.
async function mapa(req, url, cache) {
  const c = await caches.open(cache);
  const hit = await c.match(req);
  if (hit) return hit;
  const r = await fetch(req);
  if (r.ok) {
    const viejas = (await c.keys()).filter(k => new URL(k.url).pathname === url.pathname);
    await Promise.all(viejas.map(k => c.delete(k)));
    await c.put(req, r.clone());
  }
  return r;
}
