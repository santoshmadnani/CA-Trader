// CA Trader PWA Service Worker (Enables offline app shell & installation prompt)
const CACHE_NAME = 'ca-trader-shell-v1';

self.addEventListener('install', (event) => {
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener('fetch', (event) => {
  // Pass through all API and streaming requests directly
  if (event.request.url.includes('/api/') || event.request.url.includes('/ws/')) {
    return;
  }
  event.respondWith(
    fetch(event.request).catch(() => caches.match(event.request))
  );
});

