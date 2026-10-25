// After a deploy, an already-open tab still points at old hashed chunk names
// that no longer exist, so a lazy import() fails. Reload once to pick up the
// new index.html. The sessionStorage flag stops a reload loop when the
// failure is not a stale deploy (e.g. the server is genuinely down).
export const RELOAD_FLAG = "stale-chunk-reloaded";

const CHUNK_ERROR_RE =
  /Failed to fetch dynamically imported module|error loading dynamically imported module|Importing a module script failed|Unable to preload CSS/i;

export function isChunkLoadError(reason: unknown): boolean {
  const msg =
    reason instanceof Error
      ? reason.message
      : typeof reason === "string"
        ? reason
        : typeof (reason as { message?: unknown } | null)?.message === "string"
          ? (reason as { message: string }).message
          : "";
  return CHUNK_ERROR_RE.test(msg);
}

/** Reloads at most once per tab session. Returns true if it reloaded. */
export function reloadOnceForStaleChunk(
  reload: () => void = () => window.location.reload(),
  storage: Pick<Storage, "getItem" | "setItem"> = window.sessionStorage,
): boolean {
  try {
    if (storage.getItem(RELOAD_FLAG)) return false;
    storage.setItem(RELOAD_FLAG, "1");
  } catch {
    // Storage unavailable: reloading could loop forever, so don't.
    return false;
  }
  reload();
  return true;
}

export function installStaleChunkReload(): void {
  window.addEventListener("vite:preloadError", (event) => {
    if (reloadOnceForStaleChunk()) event.preventDefault();
  });
  window.addEventListener("unhandledrejection", (event) => {
    if (isChunkLoadError(event.reason)) reloadOnceForStaleChunk();
  });
  // A successful boot clears the flag after a grace period so a later deploy
  // in the same tab session can reload again.
  window.setTimeout(() => {
    try {
      window.sessionStorage.removeItem(RELOAD_FLAG);
    } catch {
      /* ignore */
    }
  }, 10_000);
}
