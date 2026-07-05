/*
 * App-shell service worker, phase-0 scope: cache the static shell for
 * fast/offline startup. Lesson-content bundle caching arrives with the
 * offline-sync APIs (POST /sync/batch) — do NOT cache authenticated
 * API responses here; personalized state must stay fresh.
 */
const SHELL_CACHE = "lingo2-shell-v1";

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(SHELL_CACHE).then((cache) => cache.addAll(["/", "/manifest.webmanifest"])),
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(keys.filter((k) => k !== SHELL_CACHE).map((k) => caches.delete(k))),
      )
      .then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  // Never intercept API calls or non-GET requests.
  if (event.request.method !== "GET" || url.pathname.startsWith("/api")) return;
  // Only handle same-origin static assets/navigation.
  if (url.origin !== self.location.origin) return;

  event.respondWith(
    fetch(event.request)
      .then((res) => {
        const copy = res.clone();
        caches.open(SHELL_CACHE).then((cache) => cache.put(event.request, copy));
        return res;
      })
      .catch(() =>
        caches
          .match(event.request)
          .then((hit) => hit ?? (event.request.mode === "navigate" ? caches.match("/") : undefined))
          .then((hit) => hit ?? Response.error()),
      ),
  );
});
