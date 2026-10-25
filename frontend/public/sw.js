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

// Pre-rendered TTS clips (/media/audio/<content-hash>.mp3, immutable). Separate
// cache so the shell cleanup below never evicts them and the shell handler
// never stores them unbounded. Cache-on-play only (nothing is precached) and
// capped: oldest entries go first once MAX_AUDIO_ENTRIES is exceeded.
const AUDIO_CACHE = "lingo2-audio-v1";
const MAX_AUDIO_ENTRIES = 400;

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
        Promise.all(keys.filter((k) => k !== SHELL_CACHE && k !== AUDIO_CACHE).map((k) => caches.delete(k))),
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

async function trimAudioCache(cache) {
  const keys = await cache.keys(); // insertion order: oldest first
  for (let i = 0; i < keys.length - MAX_AUDIO_ENTRIES; i++) await cache.delete(keys[i]);
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
