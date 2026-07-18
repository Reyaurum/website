// Place at /website/sw.js — its default scope covers everything under /website/
const CACHE_NAME = 'novel-offline-v1';

// Files every page needs — including the big data.b64 payload
const CORE_ASSETS = [
  '/website/main.js',
  '/website/main.css',
  '/website/data/data.json',
  '/website/data/data.b64'
];

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
  if (url.origin !== self.location.origin || event.request.method !== 'GET') return;

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
        .catch(() => cached); // offline + not cached: nothing more we can do
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
