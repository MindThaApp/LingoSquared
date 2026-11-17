/*
 * App-shell service worker, phase-0 scope: cache the static shell for
 * fast/offline startup. Lesson-content bundle caching arrives with the
 * offline-sync APIs (POST /sync/batch) — do NOT cache authenticated
 * API responses here; personalized state must stay fresh.
 */
// Bump a version suffix to invalidate what older workers cached under that
// name. The activate handler deletes ONLY this app's own caches (names that
// start with OWN_CACHE_PREFIX) that are not in CURRENT_CACHES; any other
// cache on the origin is left alone.
const OWN_CACHE_PREFIX = "lingo2-";
const SHELL_CACHE = "lingo2-shell-v3";
// Vite's content-hashed build output (/assets/<name>-<hash>.js|css|...).
// A hashed URL never changes content, so it is served cache-first. Capped
// like the audio cache so old deploys' chunks do not pile up forever.
const ASSET_CACHE = "lingo2-assets-v1";
const MAX_ASSET_ENTRIES = 300;
const ASSET_PATH = /^\/assets\//;
// Shown for a navigation when the network is down and nothing is cached.
const OFFLINE_URL = "/offline.html";
const PRECACHE_URLS = ["/", "/manifest.webmanifest", OFFLINE_URL, "/offline.css", "/icons/icon-192.png"];

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

// Pre-rendered TTS clips (/media/audio/<content-hash>.mp3, immutable). Separate
// cache so the shell cleanup below never evicts them and the shell handler
// never stores them unbounded. Cache-on-play only (nothing is precached) and
// capped: oldest entries go first once MAX_AUDIO_ENTRIES is exceeded.
const AUDIO_CACHE = "lingo2-audio-v1";
const MAX_AUDIO_ENTRIES = 400;
const CURRENT_CACHES = [SHELL_CACHE, ASSET_CACHE, AUDIO_CACHE];

// Defence in depth for user data: never store a response the server marked
// no-store/private (authenticated JSON, account pages). The API itself is
// never intercepted at all (NO_CACHE_PATH + cross-origin early returns).
function isStorable(res) {
  if (res.status !== 200 || res.type !== "basic") return false;
  const cc = (res.headers && res.headers.get && res.headers.get("cache-control")) || "";
  return !/no-store|private/i.test(cc);
}

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(SHELL_CACHE).then((cache) => cache.addAll(PRECACHE_URLS)),
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
        Promise.all(
          keys
            .filter((k) => k.startsWith(OWN_CACHE_PREFIX) && !CURRENT_CACHES.includes(k))
            .map((k) => caches.delete(k)),
        ),
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

// Evicts the oldest entries of one of this app's own caches (audio clips,
// hashed build assets) once it holds more than `max` entries.
async function trimCache(cache, max) {
  const keys = await cache.keys(); // insertion order: oldest first
  for (let i = 0; i < keys.length - max; i++) await cache.delete(keys[i]);
}
const trimAudioCache = (cache) => trimCache(cache, MAX_AUDIO_ENTRIES);

// Cache-first for content-hashed build assets; fills the cache on a miss.
async function assetResponse(request, waitUntil) {
  const cache = await caches.open(ASSET_CACHE);
  const hit = await cache.match(request);
  if (hit) return hit;
  const res = await fetch(request);
  if (isStorable(res)) {
    const copy = res.clone();
    waitUntil(cache.put(request, copy).then(() => trimCache(cache, MAX_ASSET_ENTRIES)).catch(() => {}));
  }
  return res;
}

// <audio> asks for byte ranges (and Safari insists on 206 answers). Serve a
// cached full body as a 206 slice; on a miss go to the network and, in the
// background, fetch + store the whole file with a plain GET for next time.
async function audioResponse(request, waitUntil) {
  const cache = await caches.open(AUDIO_CACHE);
  const hit = await cache.match(request.url);
  const range = request.headers.get("range");
  if (hit) {
    if (!range) return hit;
    const m = /^bytes=(\d*)-(\d*)$/.exec(range);
    const buf = await hit.arrayBuffer();
    if (m && (m[1] || m[2])) {
      const size = buf.byteLength;
      let start = m[1] ? parseInt(m[1], 10) : Math.max(0, size - parseInt(m[2], 10));
      let end = m[1] && m[2] ? Math.min(parseInt(m[2], 10), size - 1) : size - 1;
      if (start <= end && start < size) {
        return new Response(buf.slice(start, end + 1), {
          status: 206,
          headers: {
            "Content-Type": "audio/mpeg",
            "Content-Range": "bytes " + start + "-" + end + "/" + size,
            "Content-Length": String(end - start + 1),
          },
        });
      }
    }
    return new Response(buf, { status: 200, headers: { "Content-Type": "audio/mpeg" } });
  }
  const res = await fetch(request);
  if (res.ok && !range && res.status === 200) {
    const copy = res.clone();
    waitUntil(cache.put(request.url, copy).then(() => trimAudioCache(cache)).catch(() => {}));
  } else if (res.ok && range) {
    // Ranged answer: fetch the whole file once in the background for next time.
    waitUntil(
      fetch(request.url)
        .then((full) => (full.ok && full.status === 200 ? cache.put(request.url, full) : undefined))
        .then(() => trimAudioCache(cache))
        .catch(() => {}),
    );
  }
  return res;
}

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  if (
    event.request.method === "GET" &&
    url.origin === self.location.origin &&
    url.pathname.startsWith("/media/audio/")
  ) {
    event.respondWith(audioResponse(event.request, (p) => event.waitUntil(p)));
    return;
  }
  // Never intercept API calls or non-GET requests.
  if (event.request.method !== "GET") return;
  // Only handle same-origin static assets/navigation, minus API and the
  // heavy whisper wasm/model files (see NO_CACHE_PATH).
  if (url.origin !== self.location.origin || !isCacheablePath(url.pathname)) return;

  if (ASSET_PATH.test(url.pathname)) {
    event.respondWith(assetResponse(event.request, (p) => event.waitUntil(p)));
    return;
  }

  // Navigation and other static files: network-first, cache as fallback.
  // Offline navigation: the cached page, else the cached app shell "/",
  // else the offline fallback page.
  const isNavigate = event.request.mode === "navigate";
  event.respondWith(
    fetch(event.request)
      .then((res) => {
        // Only successful same-origin ("basic") responses; never partial
        // (206), error, opaque, redirected or no-store/private results.
        if (isStorable(res)) {
          const copy = res.clone();
          caches.open(SHELL_CACHE).then((cache) => cache.put(event.request, copy)).catch(() => {});
        }
        return res;
      })
      .catch(() =>
        caches
          .match(event.request)
          .then((hit) => hit ?? (isNavigate ? caches.match("/") : undefined))
          .then((hit) => hit ?? (isNavigate ? caches.match(OFFLINE_URL) : undefined))
          .then((hit) => hit ?? Response.error()),
      ),
  );
});
