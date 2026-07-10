import { FeedbackApi } from "@lingo/shared/api/endpoints";

// Automatic crash reporting over the EXISTING unauthenticated
// POST /feedback channel (category "app_bug") -- deliberately zero new
// backend infrastructure. Before this, a crash only ever hit
// console.error (ErrorBoundary) or nothing at all (uncaught errors /
// unhandled promise rejections), and vanished when the tab closed.
//
// Lives in frontend/src (not @lingo/shared) on purpose: it reads
// window/navigator directly, which the shared package must stay free of
// for the future mobile app.
//
// Backend bounds (GeneralFeedbackIn, backend/app/schemas/api.py):
// description <= 2000 chars, page_path <= 255 chars, client_context
// <= 5000 SERIALIZED chars total -- exceeding any of these 422s the
// whole report, so every free-text field below is truncated to keep the
// summed worst case comfortably under the client_context cap.
const MAX_DESCRIPTION_CHARS = 2000;
const MAX_PAGE_PATH_CHARS = 255;
const MAX_MESSAGE_CHARS = 300;
const MAX_STACK_CHARS = 2500;
const MAX_COMPONENT_STACK_CHARS = 1000;
const MAX_URL_CHARS = 300;

export type CrashSource = "window_error" | "unhandled_rejection" | "error_boundary";

// One report per distinct error message per page session (a rendering
// bug in a list can otherwise fire dozens of identical errors per
// second, and a crash INSIDE the reporting path could loop forever --
// dedup breaks that cycle too, since the re-entrant error carries the
// same message). Module-level, so it resets on a full page load, which
// is the intended "per page session" scope.
const reportedMessages = new Set<string>();

export function reportCrash(
  source: CrashSource,
  message: string,
  stack?: string,
  extra?: Record<string, unknown>,
): void {
  // Reporting a crash must never itself crash (or even reject) anything.
  try {
    const key = message.trim() || "(no message)";
    if (reportedMessages.has(key)) return;
    reportedMessages.add(key);

    FeedbackApi.submit({
      category: "app_bug",
      description: `[automatic crash report] ${source}: ${key}`.slice(0, MAX_DESCRIPTION_CHARS),
      page_path: window.location.pathname.slice(0, MAX_PAGE_PATH_CHARS),
      client_context: {
        auto_crash_report: true,
        source,
        message: key.slice(0, MAX_MESSAGE_CHARS),
        stack: stack ? stack.slice(0, MAX_STACK_CHARS) : undefined,
        url: window.location.href.slice(0, MAX_URL_CHARS),
        user_agent: navigator.userAgent.slice(0, MAX_URL_CHARS),
        ...extra,
      },
    }).catch(() => {
      // Offline, collector unreachable, payload rejected -- all fine.
      // Swallowing here also guarantees this promise can never feed the
      // unhandledrejection handler below and recurse.
    });
  } catch {
    // Same guarantee for the synchronous half.
  }
}

// Called once from main.tsx, after configureApi() (FeedbackApi needs the
// client configured before any report could fire).
export function installGlobalCrashReporting(): void {
  window.addEventListener("error", (event) => {
    const err: unknown = event.error;
    const message = event.message || (err instanceof Error ? err.message : String(err ?? ""));
    if (!message) return; // e.g. a resource-load error with nothing to say
    reportCrash("window_error", message, err instanceof Error ? err.stack : undefined, {
      filename: event.filename ? event.filename.slice(0, MAX_URL_CHARS) : undefined,
      line: event.lineno || undefined,
      column: event.colno || undefined,
    });
  });

  window.addEventListener("unhandledrejection", (event) => {
    const reason: unknown = event.reason;
    const message = reason instanceof Error ? reason.message : String(reason ?? "(no reason)");
    reportCrash(
      "unhandled_rejection",
      message,
      reason instanceof Error ? reason.stack : undefined,
    );
  });
}

// For ErrorBoundary.componentDidCatch: React's component stack is a
// separate diagnostic from the JS stack, truncated on its own budget.
export function truncateComponentStack(componentStack: string | null | undefined): string | undefined {
  return componentStack ? componentStack.slice(0, MAX_COMPONENT_STACK_CHARS) : undefined;
}
