/**
 * Service Worker para HHA Group PWA.
 *
 * Estrategia simple: cache-first para assets estaticos (logo, CSS),
 * network-first para API y paginas (siempre datos frescos).
 *
 * No cachea POST/PATCH/DELETE — solo GET.
 */

const CACHE_NAME = 'hha-group-v1';
const STATIC_ASSETS = [
  '/static/manifest.json',
  '/static/logo_hha.png',
  '/static/logos/animus_lab.png',
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      return cache.addAll(STATIC_ASSETS).catch(err => {
        // Si algun asset falla, no bloquear instalacion
        console.warn('[SW] Some assets failed to cache:', err);
      });
    })
  );
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(names => {
      return Promise.all(
        names.filter(n => n !== CACHE_NAME).map(n => caches.delete(n))
      );
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', event => {
  const req = event.request;

  // Solo GETs cacheables
  if (req.method !== 'GET') return;

  // No cachear API ni autenticacion ni admin
  if (req.url.includes('/api/') ||
      req.url.includes('/login') ||
      req.url.includes('/logout') ||
      req.url.includes('/admin')) {
    // Network-first: intentar red, si falla usar cache
    event.respondWith(
      fetch(req).catch(() => caches.match(req))
    );
    return;
  }

  // Static assets: cache-first
  if (req.url.includes('/static/')) {
    event.respondWith(
      caches.match(req).then(cached => {
        return cached || fetch(req).then(resp => {
          const respClone = resp.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(req, respClone));
          return resp;
        });
      })
    );
    return;
  }

  // Paginas HTML: network-first con fallback a cache
  event.respondWith(
    fetch(req).then(resp => {
      // Solo cachear respuestas exitosas
      if (resp.ok && resp.type === 'basic') {
        const respClone = resp.clone();
        caches.open(CACHE_NAME).then(cache => cache.put(req, respClone));
      }
      return resp;
    }).catch(() => caches.match(req).then(c => c || new Response('Sin conexión', {
      status: 503,
      statusText: 'Service Unavailable',
      headers: {'Content-Type': 'text/plain; charset=utf-8'}
    })))
  );
});
