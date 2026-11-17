// Il service worker di daylog: gira nel browser, separato dalle pagine, e intercetta le richieste.
// Strategia "prima la rete": con la rete tutto va come senza service worker, senza rete
// i file statici arrivano dalla cache e le pagine diventano la pagina offline.
// Le spunte e la nota (PUT, DELETE, POST) non passano di qui: offline falliscono.

// Cambiando nome alla cache, la vecchia viene cancellata all'attivazione
const CACHE = "daylog-v1";

// Scaricati all'installazione. Un solo 404 e l'installazione fallisce: lo controlla tests/test_pwa.py
const PRECACHE = [
  "/offline",
  "/static/pico.classless.min.css",
  "/static/style.css",
  "/static/htmx.min.js",
  "/static/icons/icon-192.png"
];

self.addEventListener("install", (event) => {
  // Il browser aspetta la promessa: se fallisce, il service worker non si installa
  event.waitUntil(caches.open(CACHE).then((cache) => cache.addAll(PRECACHE)));
  // Il nuovo service worker prende il posto del vecchio senza aspettare che si chiudano le schede
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((nomi) => Promise.all(nomi.filter((n) => n !== CACHE).map((n) => caches.delete(n))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const richiesta = event.request;
  const url = new URL(richiesta.url);
  // Solo le letture del nostro sito; tutto il resto va alla rete come se non ci fossimo
  if (richiesta.method !== "GET" || url.origin !== self.location.origin) {
    return;
  }

  if (richiesta.mode === "navigate") {
    // Una pagina intera: sempre dalla rete, mai una copia vecchia; senza rete la pagina offline
    event.respondWith(fetch(richiesta).catch(() => caches.match("/offline")));
  } else if (url.pathname.startsWith("/static/")) {
    // Un file statico: dalla rete, aggiornando la cache; senza rete l'ultima copia
    event.respondWith(
      fetch(richiesta)
        .then((risposta) => {
          if (risposta.ok) {
            const copia = risposta.clone();
            caches.open(CACHE).then((cache) => cache.put(richiesta, copia));
          }
          return risposta;
        })
        .catch(() => caches.match(richiesta))
    );
  }
});
