/**
 * Service Worker para EOS / HHA Group PWA.
 *
 * v3 (Sebastián 5-jun-2026) · REESCRITO tras incidente "Cargando… eterno":
 * el SW anterior cacheaba páginas HTML (network-first con fallback a caché) y
 * podía dejar al usuario atrapado en una versión vieja de una página o colgar
 * un fetch. Ahora el SW NO toca páginas ni API: ésas van SIEMPRE a la red
 * nativa del navegador (no las intercepta → imposible que las cuelgue o sirva
 * viejas). El SW solo cachea assets estáticos (logos) para velocidad/offline.
 *
 * Al activarse borra TODAS las cachés viejas (incluida la v1 que guardaba HTML)
 * y reclama los clientes → los navegadores atrapados se curan al recargar.
 */

const CACHE_NAME = 'eos-static-v3';
const STATIC_ASSETS = [
  '/static/manifest.json',
  '/static/logo_hha.png',
  '/static/logos/animus_lab.png',
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      return cache.addAll(STATIC_ASSETS).catch(err => {
        console.warn('[SW] Some assets failed to cache:', err);
      });
    })
  );
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(names => {
      // Borra TODA caché que no sea la actual (purga el HTML viejo de v1/v2).
      return Promise.all(names.filter(n => n !== CACHE_NAME).map(n => caches.delete(n)));
    }).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', event => {
  const req = event.request;

  // Solo nos metemos con assets estáticos por GET. Todo lo demás (páginas,
  // navegaciones, /api/, login, admin) → red nativa del navegador, SIN
  // respondWith: el SW no puede colgarlo ni servir una versión vieja.
  if (req.method !== 'GET') return;
  if (req.mode === 'navigate') return;

  const url = req.url;
  const esEstatico = url.includes('/static/') &&
    !url.includes('/static/sw.js');  // nunca cachear el propio SW

  if (!esEstatico) return;  // páginas + API + resto → red directa

  // Assets estáticos: cache-first, refresca en segundo plano.
  event.respondWith(
    caches.match(req).then(cached => {
      const red = fetch(req).then(resp => {
        if (resp && resp.ok && resp.type === 'basic') {
          const clone = resp.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(req, clone));
        }
        return resp;
      }).catch(() => cached);
      return cached || red;
    })
  );
});
