// FT-710 Service Worker — basic offline cache
const CACHE = 'ft710-v6';
const ASSETS = [
    '/',
    '/index.html',
    '/ft710.css',
    '/ft710_main.js',
    '/ft710_ui.js',
    '/modules/ptt_manager.js',
    '/modules/settings_manager.js',
    '/manifest.json',
];

self.addEventListener('install', function(e) {
    e.waitUntil(
        caches.open(CACHE).then(function(cache) {
            return cache.addAll(ASSETS);
        }).then(function() {
            return self.skipWaiting();
        })
    );
});

self.addEventListener('activate', function(e) {
    e.waitUntil(
        caches.keys().then(function(keys) {
            return Promise.all(keys.map(function(key) {
                if (key !== CACHE) return caches.delete(key);
            }));
        }).then(function() {
            return self.clients.claim();
        })
    );
});

self.addEventListener('fetch', function(e) {
    e.respondWith(
        caches.open(CACHE).then(function(cache) {
            return cache.match(e.request).then(function(resp) {
                return resp || fetch(e.request);
            });
        })
    );
});
