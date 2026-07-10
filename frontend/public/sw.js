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

/*
 * Web push (Phase E4). Payload contract (docs/CONTRACT.md, "Web push
 * notifications"): JSON { title, body, url } — url is an app-relative
 * path. Unknown extra fields are ignored, never an error.
 */
self.addEventListener("push", (event) => {
  let payload = {};
  try {
    payload = event.data ? event.data.json() : {};
  } catch {
    // Non-JSON payload (shouldn't happen from our backend, but a push
    // service test tool can send plain text) — show it honestly.
    payload = { body: event.data ? event.data.text() : "" };
  }
  event.waitUntil(
    self.registration.showNotification(payload.title || "Lingo²", {
      body: payload.body || "",
      icon: "/icons/icon-192.png",
      badge: "/icons/icon-192.png",
      data: { url: typeof payload.url === "string" ? payload.url : "/" },
    }),
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const url = (event.notification.data && event.notification.data.url) || "/";
  event.waitUntil(
    self.clients
      .matchAll({ type: "window", includeUncontrolled: true })
      .then((clients) => {
        // Reuse an existing app tab when one is open; otherwise open one.
        for (const client of clients) {
          if (new URL(client.url).origin === self.location.origin && "focus" in client) {
            if ("navigate" in client) client.navigate(url);
            return client.focus();
          }
        }
        return self.clients.openWindow(url);
      }),
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
