self.addEventListener('install', (e) => {
  self.skipWaiting();
});
self.addEventListener('activate', (e) => {
  self.clients.claim();
});
self.addEventListener('fetch', (e) => {
  // pass-through بسيط، ما نحتاج كاش حاليًا
});
