// Service worker de TagStudio: permite instalar la app.
// No guarda nada en caché a propósito: siempre se usa la última versión publicada.
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', e => e.waitUntil(self.clients.claim()));
