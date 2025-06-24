self.addEventListener('install', event => {
    console.log('Service Worker installed.');
});

self.addEventListener('fetch', event => {
    // Handle caching here in future
});
