/*
 * App-shell service worker, phase-0 scope: cache the static shell for
 * fast/offline startup. Lesson-content bundle caching arrives with the
 * offline-sync APIs (POST /sync/batch) — do NOT cache authenticated
 * API responses here; personalized state must stay fresh.
 */
// Bump the version suffix to invalidate everything cached by older workers;
// the activate handler deletes every cache whose name is not this one.
const SHELL_CACHE = "lingo2-shell-v2";

// Never cached: the API, and the big on-device speech files (ONNX wasm,
// model weights, sourcemaps) which would blow the storage quota.
const NO_CACHE_PATH = /^\/api(\/|$)|\.(?:wasm|onnx|bin|gguf|safetensors|map)$/i;

function isCacheablePath(pathname) {
  return !NO_CACHE_PATH.test(pathname);
}

// Push payload urls are untrusted: resolve against our origin and fall back
// to "/" for anything that is not same-origin http(s).
function safeSameOriginUrl(raw) {
  try {
    const u = new URL(typeof raw === "string" ? raw : "/", self.location.origin);
    if (u.origin !== self.location.origin) return "/";
    return u.pathname + u.search + u.hash;
  } catch {
    return "/";
  }
}

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(SHELL_CACHE).then((cache) => cache.addAll(["/", "/manifest.webmanifest"])),
  );
  // No skipWaiting(): a new worker waits until every tab running the old one
  // is closed or navigated away, so a lesson in progress is never swapped
  // under a running page (its lazy chunks would vanish). The next
  // navigation after the old tabs are gone picks up the new version.
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
    self.registration.showNotification(payload.title || "Auvel", {
      body: payload.body || "",
      icon: "/icons/icon-192.png",
      badge: "/icons/icon-192.png",
      data: { url: safeSameOriginUrl(payload.url) },
    }),
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const url = safeSameOriginUrl(event.notification.data && event.notification.data.url);
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
  if (event.request.method !== "GET") return;
  // Only handle same-origin static assets/navigation, minus API and the
  // heavy whisper wasm/model files (see NO_CACHE_PATH).
  if (url.origin !== self.location.origin || !isCacheablePath(url.pathname)) return;

  event.respondWith(
    fetch(event.request)
      .then((res) => {
        // Only successful same-origin ("basic") responses; never partial
        // (206), error, opaque or redirected results.
        if (res.status === 200 && res.type === "basic") {
          const copy = res.clone();
          caches.open(SHELL_CACHE).then((cache) => cache.put(event.request, copy)).catch(() => {});
        }
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
