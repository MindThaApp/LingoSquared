// Web push subscribe/unsubscribe helpers (Phase E4). See
// docs/CONTRACT.md's "Web push notifications" section for the endpoint
// and payload contract this implements.
//
// Support/config gating convention (same "hidden, not disabled" pattern
// as SpeakButton/speak()'s provider chain): push UI must only render
// when BOTH isPushSupported() (browser capability — iOS Safari outside
// an installed PWA has no PushManager) AND the server's
// GET /push/vapid-public-key probe reports configured: true. When VAPID
// keys aren't provisioned server-side the whole feature no-ops
// invisibly — never a broken button.
import { PushApi } from "@lingo/shared/api/endpoints";

// Per-device dismissal of the HomePage prompt, same localStorage
// precedent as the voice/speed/mic preferences.
const PROMPT_DISMISSED_KEY = "push-prompt-dismissed";

export function isPushSupported(): boolean {
  return (
    typeof window !== "undefined" &&
    "serviceWorker" in navigator &&
    "PushManager" in window &&
    "Notification" in window
  );
}

export function isPushPromptDismissed(): boolean {
  try {
    return localStorage.getItem(PROMPT_DISMISSED_KEY) === "1";
  } catch {
    return false;
  }
}

export function dismissPushPrompt(): void {
  try {
    localStorage.setItem(PROMPT_DISMISSED_KEY, "1");
  } catch {
    // Private-browsing/quota errors: the prompt just reappears next visit.
  }
}

// pushManager.subscribe() wants the raw VAPID public-key bytes, but the
// backend serves it in the standard base64url text form.
// Explicit Uint8Array<ArrayBuffer> (not the default ArrayBufferLike):
// TS 5.7+ DOM typings require applicationServerKey's BufferSource to be
// backed by a real ArrayBuffer, never a SharedArrayBuffer.
function urlBase64ToUint8Array(base64Url: string): Uint8Array<ArrayBuffer> {
  const padding = "=".repeat((4 - (base64Url.length % 4)) % 4);
  const base64 = (base64Url + padding).replace(/-/g, "+").replace(/_/g, "/");
  const raw = atob(base64);
  const output = new Uint8Array(new ArrayBuffer(raw.length));
  for (let i = 0; i < raw.length; i += 1) output[i] = raw.charCodeAt(i);
  return output;
}

async function serviceWorkerRegistration(): Promise<ServiceWorkerRegistration> {
  // main.tsx only registers sw.js in production builds; registering it
  // again here is idempotent (same script URL/scope) and makes push work
  // against a dev server too.
  await navigator.serviceWorker.register("/sw.js");
  return navigator.serviceWorker.ready;
}

/** The browser's current push subscription for this origin, if any —
 * does NOT prompt for permission or touch the network. */
export async function getExistingPushSubscription(): Promise<PushSubscription | null> {
  if (!isPushSupported()) return null;
  try {
    const registration = await navigator.serviceWorker.getRegistration();
    if (!registration) return null;
    return await registration.pushManager.getSubscription();
  } catch {
    return null;
  }
}

/** Whether the server has VAPID keys provisioned at all. Unauthenticated
 * probe; false means hide every push surface. */
export async function isPushConfiguredOnServer(): Promise<boolean> {
  try {
    return (await PushApi.vapidPublicKey()).configured;
  } catch {
    // Can't reach the endpoint (old backend, network) — treat as
    // unconfigured and stay hidden rather than showing UI that can't work.
    return false;
  }
}

export type SubscribeOutcome =
  | "subscribed"
  | "permission_denied"
  | "unsupported"
  | "not_configured";

/** Full subscribe flow: capability check → server-config probe →
 * Notification permission prompt → PushManager.subscribe →
 * POST /push/subscribe. Throws on unexpected failures (network,
 * push-service errors); returns a discriminated outcome for the
 * expected non-error endings so callers can message them honestly. */
export async function subscribeToPush(): Promise<SubscribeOutcome> {
  if (!isPushSupported()) return "unsupported";
  const vapid = await PushApi.vapidPublicKey();
  if (!vapid.configured || !vapid.public_key) return "not_configured";

  const permission = await Notification.requestPermission();
  if (permission !== "granted") return "permission_denied";

  const registration = await serviceWorkerRegistration();
  // Reuse an existing subscription when one exists — subscribing again
  // with a (rotated) different applicationServerKey would throw
  // InvalidStateError, and the backend upserts by endpoint anyway.
  const subscription =
    (await registration.pushManager.getSubscription()) ??
    (await registration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(vapid.public_key),
    }));

  const json = subscription.toJSON();
  if (!json.endpoint || !json.keys?.p256dh || !json.keys?.auth) {
    // A subscription without encryption keys can never be pushed to —
    // drop it rather than registering a dead row server-side.
    await subscription.unsubscribe().catch(() => {});
    throw new Error("Browser produced an incomplete push subscription");
  }
  await PushApi.subscribe({
    endpoint: json.endpoint,
    keys: { p256dh: json.keys.p256dh, auth: json.keys.auth },
  });
  return "subscribed";
}

/** Unsubscribes this device: browser-side first (the part the user can
 * see), then best-effort server cleanup — the server prunes dead
 * subscriptions on its next send anyway (404/410), so a failed cleanup
 * call is not worth surfacing. */
export async function unsubscribeFromPush(): Promise<void> {
  const subscription = await getExistingPushSubscription();
  if (!subscription) return;
  const endpoint = subscription.endpoint;
  await subscription.unsubscribe();
  try {
    await PushApi.unsubscribe(endpoint);
  } catch {
    // Server row becomes a dead subscription, pruned on next send.
  }
}
