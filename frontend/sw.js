const CACHE_NAME = 'warracker-cache-v2';
const urlsToCache = [
  './',
  './index.html',
  './settings-new.html',
  './status.html',
  './style.css?v=20250529005',
  './settings-styles.css?v=20250529005',
  './header-fix.css?v=20250529005',
  './mobile-header.css?v=20250529005',
  './script.js?v=20250529005',
  './auth.js?v=20250529005',
  './settings-new.js?v=20250529005',
  './manifest.json',
  './img/favicon-16x16.png',
  './img/favicon-32x32.png',
  './img/favicon-512x512.png' 
  // Add other important assets here, especially icons declared in manifest.json
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('Opened cache');
        return cache.addAll(urlsToCache);
      })
  );
});

self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request)
      .then(response => {
        // Cache hit - return response
        if (response) {
          return response;
        }
        return fetch(event.request);
      }
    )
  );
});

self.addEventListener('activate', event => {
  const cacheWhitelist = [CACHE_NAME];
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheWhitelist.indexOf(cacheName) === -1) {
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
}); 