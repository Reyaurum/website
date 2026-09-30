const CACHE_NAME = 'novel-offline-v9';
const INDEX = '/website/index.html';
const MATCH_OPTS = { ignoreSearch: true, ignoreVary: true };

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
const CRITICAL = [
  '/website/index.html',               // manifest start_url — must be cached or offline launches fail immediately
  '/website/homepage.js',
  '/website/homepage.css',
  '/website/manifest.json',
  '/website/main.js',
  '/website/main.css',
  '/website/data/data.json',
  '/website/data/data.b64'
];

const offlineFallback = () =>
  new Response('Not available offline.', { status: 503, headers: { 'Content-Type': 'text/plain' } });

const match = (req) => caches.match(req, MATCH_OPTS);

// Safari rejects navigation responses that are flagged as redirected — rebuild them clean
async function clean(res) {
  if (!res.redirected) return res;
  return new Response(await res.blob(), {
    status: res.status, statusText: res.statusText, headers: res.headers
  });
}

self.addEventListener('install', (event) => {
  self.skipWaiting();
  event.waitUntil((async () => {
    const cache = await caches.open(CACHE_NAME);

    // Critical shell: if any of these fail, fail the install so we never
    // activate a broken cache (the old SW keeps running instead).
    await Promise.all(CRITICAL.map(async (url) => {
      const res = await fetch(url, { cache: 'reload' });
      if (!res.ok) throw new Error('Failed to cache ' + url + ' (' + res.status + ')');
      await cache.put(url, await clean(res));
    }));

    // Big / optional stuff: best effort
    const rest = CORE_ASSETS.filter((u) => !CRITICAL.includes(u));
    const results = await Promise.allSettled(rest.map((u) => cache.add(new Request(u, { cache: 'reload' }))));
    results.forEach((r, i) => r.status === 'rejected' && console.error('Failed to cache', rest[i], r.reason));
  })());
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') return;
  if (new URL(event.request.url).origin !== location.origin) return;

  if (event.request.mode === 'navigate') {
    event.respondWith((async () => {
      const cached = await match(event.request);
      if (cached) return clean(cached);
      try {
        const res = await fetch(event.request);
        if (res.ok && !res.redirected) {
          const copy = res.clone();
          caches.open(CACHE_NAME).then((c) => c.put(event.request, copy));
        }
        return res;
      } catch {
        // Offline and this exact page isn't cached: fall back to the app shell
        const shell = await match(INDEX);
        return shell ? clean(shell) : offlineFallback();
      }
    })());
    return;
  }

  event.respondWith((async () => {
    const cached = await match(event.request);
    if (cached) return cached;
    try {
      const res = await fetch(event.request);
      if (res.ok && res.status === 200) {
        const copy = res.clone();
        caches.open(CACHE_NAME).then((c) => c.put(event.request, copy));
      }
      return res;
    } catch {
      return offlineFallback();
    }
  })());
});