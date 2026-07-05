// FT-710 Service Worker — basic offline cache
const CACHE = 'ft710-v1';
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
        })
    );
});

self.addEventListener('fetch', function(e) {
    e.respondWith(
        caches.match(e.request).then(function(resp) {
            return resp || fetch(e.request);
        })
    );
});
