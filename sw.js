const ONBELLEK_ADI = "syfinans-v3";
const ONBELLEK_DOSYALARI = [
  "/",
  "/manifest.json",
  "/icons/icon-72x72.png",
  "/icons/icon-96x96.png",
  "/icons/icon-128x128.png",
  "/icons/icon-144x144.png",
  "/icons/icon-152x152.png",
  "/icons/icon-192x192.png",
  "/icons/icon-384x384.png",
  "/icons/icon-512x512.png",
  "/icons/maskable-icon-192x192.png",
  "/icons/maskable-icon-512x512.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(ONBELLEK_ADI).then((cache) => cache.addAll(ONBELLEK_DOSYALARI))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((anahtarlar) =>
      Promise.all(
        anahtarlar
          .filter((k) => k !== ONBELLEK_ADI)
          .map((k) => caches.delete(k))
      )
    )
  );
  self.clients.claim();
});

// API çağrılarını hiç önbelleğe alma (her zaman canlı veri) - sadece uygulama kabuğu/ikonlar için cache-first.
self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  if (url.pathname.startsWith("/api/")) {
    return; // ağdan geçsin, servis çalışanı araya girmesin
  }
  event.respondWith(
    caches.match(event.request).then((cevap) => cevap || fetch(event.request))
  );
});