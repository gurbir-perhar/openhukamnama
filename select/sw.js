self.addEventListener('install', event => {
  event.waitUntil(
    caches.open('hukamnama-cache').then(cache => {
      return cache.addAll([
        './',
        './index.html',
        './manifest.json',
        './icon-192x192.png',
        './icon-512x512.png',
        'https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css',
        'https://cdn.datatables.net/1.10.21/css/jquery.dataTables.min.css',
        'https://cdn.datatables.net/select/1.3.1/css/select.dataTables.min.css',
        'https://code.jquery.com/jquery-3.5.1.min.js',
        'https://cdn.datatables.net/1.10.21/js/jquery.dataTables.min.js',
        'https://cdn.datatables.net/select/1.3.1/js/dataTables.select.min.js',
      ]);
    })
  );
});

self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request).then(response => {
      return response || fetch(event.request);
    })
  );
});