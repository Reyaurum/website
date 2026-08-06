// Place at /website/sw.js — its default scope covers everything under /website/
const CACHE_NAME = 'novel-offline-v4'; // bump this any time cached assets or fetch logic change

// Files every page needs — including the big data.b64 payload
const CORE_ASSETS = [
  '/website/index.html',               // manifest start_url — must be cached or offline launches fail immediately
  '/website/homepage.js',
  '/website/homepage.css',
  '/website/manifest.json',
  '/website/main.js',
  '/website/main.css',
  '/website/data/data.json',
  '/website/data/data.b64'
];

// event.respondWith() MUST resolve to a real Response — resolving to undefined
// (e.g. from a naive .catch(() => cached) when cached is also undefined) is what
// produces "FetchEvent.respondWith() received an error: Returned response is null."
// Every code path below funnels through this instead of ever returning nothing.
const offlineFallback = () =>
  new Response('Not available offline.', {
    status: 503,
    statusText: 'Offline',
    headers: { 'Content-Type': 'text/plain' }
  });

self.addEventListener('install', (event) => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME).then(async (cache) => {
      // add() each file individually — addAll() aborts the WHOLE install if any one fails
      const results = await Promise.allSettled(CORE_ASSETS.map((url) => cache.add(url)));
      results.forEach((r, i) => {
        if (r.status === 'rejected') console.error('Failed to cache', CORE_ASSETS[i], r.reason);
      });
    })
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

// Cache-first for same-origin requests; falls back to network, and stores new
// chapter pages the first time they're visited online.
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);
  if (event.request.method !== 'GET') return;

  // Navigations get special handling: never resolve one with a response that
  // internally followed a redirect (cached.redirected / response.redirected).
  // Safari hard-fails the load if we do — the redirect has to happen at the
  // navigation level, not be swallowed by the service worker.
  if (event.request.mode === 'navigate') {
    event.respondWith(
      caches.match(event.request)
        .then((cached) => {
          if (cached) return cached;
          return fetch(event.request).then((response) => {
            // Cache it for next time — but never a redirected response (same rule as before).
            if (response.ok && !response.redirected) {
              const clone = response.clone();
              caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
            }
            return response;
          });
        })
        .catch(async () => (await caches.match(event.request)) || offlineFallback())
    );
    return;
  }

  event.respondWith(
    caches.match(event.request).then((cached) => {
      if (cached) return cached;
      return fetch(event.request)
        .then((response) => {
          if (response.ok) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
          }
          return response;
        })
        .catch(() => cached || offlineFallback()); // always a real Response, never undefined
    })
  );
});

// The page can ask the SW to pre-fetch a batch of chapter URLs on demand
// (see downloadAllForOffline() below) instead of waiting for the user to visit each one.
self.addEventListener('message', (event) => {
  if (event.data?.type === 'CACHE_CHAPTERS') {
    event.waitUntil(
      caches.open(CACHE_NAME).then((cache) =>
        Promise.allSettled(event.data.urls.map((u) => cache.add(u)))
      )
    );
  }
});