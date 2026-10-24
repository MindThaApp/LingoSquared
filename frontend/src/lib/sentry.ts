import * as Sentry from "@sentry/react";
import { FeedbackApi } from "@lingo/shared/api/endpoints";
import { getCrashConsent } from "./crashConsent";
import { collectReportTags } from "./reportContext";
import { scrubEvent } from "./sentryScrub";

// Crash reporting + learner-initiated problem reports through Sentry.
//
// Two different consent situations, kept apart on purpose:
//  - Automatic crash events need the learner's say-so (Never / Ask /
//    Always). Nothing is sent before that: the SDK's own global handlers
//    are switched off, and beforeSend drops any error event that was not
//    explicitly approved by this module.
//  - "Report a problem" is an explicit action, so it is sent whatever the
//    consent setting says.
// With no DSN (tests, local dev, forks) the SDK is never initialised and
// every function here degrades to a no-op / the existing feedback endpoint.

const dsn = (import.meta.env.VITE_SENTRY_DSN ?? "").trim();

export function isSentryEnabled(): boolean {
  return dsn !== "";
}

export function sentryEnvironment(): string {
  return (
    import.meta.env.VITE_SENTRY_ENVIRONMENT ||
    (import.meta.env.PROD ? "production.lan" : "development")
  );
}

// Errors the learner (or "always" mode) has approved for sending.
const approved = new WeakSet<object>();

export function initSentry(): boolean {
  if (!isSentryEnabled()) return false;
  Sentry.init({
    dsn,
    release: import.meta.env.VITE_SENTRY_RELEASE || undefined,
    environment: sentryEnvironment(),
    // SDK 11 replaced sendDefaultPii with dataCollection: collect none of it.
    dataCollection: {
      userInfo: false,
      cookies: false,
      httpHeaders: false,
      httpBodies: [],
      urlQueryParams: false,
    },
    tracesSampleRate: 0,
    // We install our own handlers so consent can gate them.
    integrations: (defaults) => defaults.filter((i) => i.name !== "GlobalHandlers"),
    beforeBreadcrumb: (b) => (b.category === "console" ? null : b),
    beforeSend(event, hint) {
      const original = hint?.originalException;
      const ok =
        getCrashConsent() === "always" ||
        (typeof original === "object" && original !== null && approved.has(original));
      if (!ok || getCrashConsent() === "never") return null;
      return scrubEvent(event);
    },
  });
  return true;
}

// A crash waiting for the learner's answer in Ask mode. Several senders can
// queue on the same prompt (Sentry and the app's own feedback reporter).
export interface PendingCrash {
  sends: Array<() => void>;
}

type Listener = (pending: PendingCrash | null) => void;
const listeners = new Set<Listener>();
let pending: PendingCrash | null = null;

export function subscribePendingCrash(fn: Listener): () => void {
  listeners.add(fn);
  fn(pending);
  return () => {
    listeners.delete(fn);
  };
}

function setPending(next: PendingCrash | null) {
  pending = next;
  listeners.forEach((fn) => fn(next));
}

function sendToSentry(error: Error, componentStack?: string) {
  approved.add(error);
  Sentry.withScope((scope) => {
    scope.setTags(collectReportTags(window.location.pathname));
    if (componentStack) scope.setExtra("component_stack", componentStack.slice(0, 1000));
    Sentry.captureException(error);
  });
}

function toError(value: unknown): Error {
  if (value instanceof Error) return value;
  return new Error(typeof value === "string" ? value : "Unknown error");
}

// The single consent gate for every automatic crash report. Never: nothing
// is sent. Always: send now. Ask: hold the sender until the learner answers.
export function sendWithCrashConsent(send: () => void): void {
  try {
    const consent = getCrashConsent();
    if (consent === "never") return;
    if (consent === "always") {
      send();
      return;
    }
    setPending({ sends: [...(pending?.sends ?? []), send] });
  } catch {
    // Reporting must never be the thing that crashes the app.
  }
}

// Entry point for every unhandled error going to Sentry.
export function handleCrash(value: unknown, componentStack?: string): void {
  if (!isSentryEnabled()) return;
  const error = toError(value);
  sendWithCrashConsent(() => sendToSentry(error, componentStack));
}

export function answerPendingCrash(sendIt: boolean): void {
  const crash = pending;
  setPending(null);
  if (crash && sendIt) {
    for (const send of crash.sends) {
      try {
        send();
      } catch {
        // ignore
      }
    }
  }
}

export function installCrashCapture(): void {
  window.addEventListener("error", (event) => {
    if (!event.error && !event.message) return;
    handleCrash(event.error ?? event.message);
  });
  window.addEventListener("unhandledrejection", (event) => {
    handleCrash(event.reason);
  });
}

export interface ProblemReport {
  message: string;
  email?: string;
}

// Explicit report from the "Report a problem" form. Always sent.
export async function sendProblemReport({ message, email }: ProblemReport): Promise<void> {
  const tags = {
    ...collectReportTags(window.location.pathname),
    release: import.meta.env.VITE_SENTRY_RELEASE || "unknown",
    environment: sentryEnvironment(),
  };
  const trimmedEmail = email?.trim() || undefined;
  if (isSentryEnabled()) {
    Sentry.captureFeedback({ message, email: trimmedEmail, tags });
    await Sentry.flush(2000);
    return;
  }
  // No Sentry configured: fall back to the app's own feedback endpoint so
  // the learner's report still reaches us.
  await FeedbackApi.submit({
    category: "app_bug",
    description: message.slice(0, 2000),
    page_path: window.location.pathname.slice(0, 255),
    client_context: { ...tags, contact_email: trimmedEmail },
  });
}
