const CACHE_NAME = 'warracker-cache-v20251024001';
const urlsToCache = [
  // HTML pages
  './',
  './index.html',
  './status.html',
  './settings-new.html',
  './about.html',
  './login.html',
  './register.html',
  './reset-password.html',
  './reset-password-request.html',
  './auth-redirect.html',
  './debug-export.html',

  // Stylesheets (versioned)
  './style.css?v=20250119004',
  './styles.css?v=20250119001',
  './settings-styles.css?v=20250119001',
  './header-fix.css?v=20250119001',
  './mobile-header.css?v=20250119002',

  // JavaScript (versioned)
  './script.js?v=20250119002',
  './auth.js?v=20250119001',
  './settings-new.js?v=20250119001',
  './status.js?v=20250119001',
  './theme-loader.js?v=20250119001',
  './footer-fix.js?v=20251024001',
  './footer-content.js?v=20250119001',
  './include-auth-new.js?v=20250119001',
  './file-utils.js?v=20250119001',
  './fix-auth-buttons-loader.js?v=20250119001',
  './auth-redirect.js?v=20250119001',
  './mobile-menu.js?v=20250119002',
  './version-checker.js?v=20250119001',

  // i18n libraries and config (versioned)
  './js/i18n.js?v=20250119001',
  './js/lib/i18next.min.js?v=20250119001',
  './js/lib/i18nextHttpBackend.min.js?v=20250119001',
  './js/lib/i18nextBrowserLanguageDetector.min.js?v=20250119001',

  // Charts
  './chart.js?v=20250119001',

  // App manifest and icons
  './manifest.json',
  './favicon.ico',
  './img/favicon-16x16.png?v=2',
  './img/favicon-32x32.png?v=2',
  './img/favicon-512x512.png'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('Opened cache');
        return cache.addAll(urlsToCache);
      })
  );
  // Activate the new service worker immediately after installation
  self.skipWaiting();
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
    }).then(() => self.clients.claim())
  );
}); 