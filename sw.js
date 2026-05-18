/*
 * waterpipe service worker — bump CACHE_VERSION when you ship new files.
 * Strategy:
 *   - same-origin GET → cache-first, fall back to network, then update cache
 *   - cross-origin (fonts.googleapis.com etc) → network-first, cached as backup
 *   - non-GET / range requests → pass through to network
 * On activate: deletes old caches so stale assets get purged.
 */

const CACHE_VERSION = 'wp-v5-2026-05-18';
const PRECACHE = [
  './',
  './index.html',
  './manifest.webmanifest',
  './icons/icon-192.png',
  './icons/icon-512.png',
  './icons/apple-touch-icon.png',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_VERSION).then((cache) => cache.addAll(PRECACHE))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_VERSION).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;
  if (req.headers.has('range')) return;

  const url = new URL(req.url);
  const sameOrigin = url.origin === self.location.origin;

  if (sameOrigin) {
    // cache-first: 離線可用是 PWA 重點
    event.respondWith(
      caches.match(req).then((cached) => {
        if (cached) {
          // 背景更新（stale-while-revalidate 的精簡版）
          fetch(req).then((res) => {
            if (res && res.ok) {
              caches.open(CACHE_VERSION).then((c) => c.put(req, res.clone()));
            }
          }).catch(() => {});
          return cached;
        }
        return fetch(req).then((res) => {
          if (res && res.ok && res.type === 'basic') {
            const clone = res.clone();
            caches.open(CACHE_VERSION).then((c) => c.put(req, clone));
          }
          return res;
        }).catch(() => caches.match('./index.html'));
      })
    );
    return;
  }

  // 跨來源（Google Fonts 之類）→ network-first, cache as fallback
  event.respondWith(
    fetch(req).then((res) => {
      if (res && res.ok) {
        const clone = res.clone();
        caches.open(CACHE_VERSION).then((c) => c.put(req, clone));
      }
      return res;
    }).catch(() => caches.match(req))
  );
});
