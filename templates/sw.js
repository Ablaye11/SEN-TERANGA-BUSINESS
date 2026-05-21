const CACHE_NAME = 'sen-teranga-cache-v1';
const ASSETS_TO_CACHE = [
    '/sales/pos/',
    '/static/css/style.css',
    '/static/images/logo.png',
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css',
    'https://unpkg.com/html5-qrcode'
];

// Install event: Caches critical assets
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            console.log('[Service Worker] Pre-caching offline shell');
            return cache.addAll(ASSETS_TO_CACHE);
        }).then(() => self.skipWaiting())
    );
});

// Activate event: Cleans up old caches
self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames.map((cache) => {
                    if (cache !== CACHE_NAME) {
                        console.log('[Service Worker] Removing old cache:', cache);
                        return caches.delete(cache);
                    }
                })
            );
        }).then(() => self.clients.claim())
    );
});

// Fetch event: Network-first falling back to Cache strategy for POS page and static assets,
// but ignore dynamic APIs and Django admin
self.addEventListener('fetch', (event) => {
    const url = new URL(event.request.url);

    // Bypass caching for APIs, POST requests and Django Admin
    if (url.pathname.includes('/api/') || 
        url.pathname.includes('/admin/') || 
        event.request.method !== 'GET') {
        return; // Let the browser handle normally
    }

    const isStaticAsset = ASSETS_TO_CACHE.includes(url.pathname) || 
                          url.pathname.startsWith('/static/') ||
                          url.hostname === 'cdnjs.cloudflare.com' ||
                          url.hostname === 'unpkg.com';

    if (isStaticAsset && url.pathname !== '/sales/pos/') {
        // Stratégie Cache-First pour les assets statiques (extrêmement rapide)
        event.respondWith(
            caches.match(event.request).then((cachedResponse) => {
                if (cachedResponse) return cachedResponse;
                return fetch(event.request).then((response) => {
                    if (response.status === 200) {
                        const responseClone = response.clone();
                        caches.open(CACHE_NAME).then((cache) => cache.put(event.request, responseClone));
                    }
                    return response;
                });
            })
        );
    } else {
        // Stratégie Network-First avec Timeout (3 secondes max) pour la page POS
        event.respondWith(
            new Promise((resolve, reject) => {
                const timeoutId = setTimeout(() => reject(new Error("Timeout")), 3000);
                fetch(event.request).then(response => {
                    clearTimeout(timeoutId);
                    if (response.status === 200 && url.pathname === '/sales/pos/') {
                        const responseClone = response.clone();
                        caches.open(CACHE_NAME).then((cache) => cache.put(event.request, responseClone));
                    }
                    resolve(response);
                }).catch(err => {
                    clearTimeout(timeoutId);
                    reject(err);
                });
            }).catch(() => {
                return caches.match(event.request).then((cachedResponse) => {
                    if (cachedResponse) return cachedResponse;
                    if (url.pathname === '/sales/pos/') return caches.match('/sales/pos/');
                });
            })
        );
    }
});
