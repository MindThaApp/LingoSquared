import { useEffect, useState, type ReactNode } from "react";
import { Navigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { readCachedUser, useAuth } from "../../auth/AuthContext";

// The screen for auth status "unverified": a session exists in storage but
// the app could not reach the backend to verify it (offline device,
// backend restart, 5xx). It lives next to the route guard because that is
// the only place that decides what an unverified session may see —
// LoginPage renders the same component so that manually navigating to
// /login in this state can't hand the user the "continue as guest" button
// either (that click orphans the account they already have; see the
// AuthStatus comment in AuthContext.tsx).
export function SessionUnavailableScreen() {
  const { t } = useTranslation();
  const { retrySession, retrying, logout } = useAuth();

  // Offline vs "reachable network, unreachable server" are different
  // messages: the first is expected and self-healing, the second isn't.
  const [online, setOnline] = useState(
    () => typeof navigator === "undefined" || navigator.onLine !== false,
  );
  useEffect(() => {
    const update = () => setOnline(navigator.onLine !== false);
    window.addEventListener("online", update);
    window.addEventListener("offline", update);
    return () => {
      window.removeEventListener("online", update);
      window.removeEventListener("offline", update);
    };
  }, []);

  // Read once on mount — localStorage isn't reactive and the cached user
  // can't change while this screen is up.
  const [cachedUser] = useState(readCachedUser);

  return (
    <div className="auth-page">
      <div className="card" style={{ textAlign: "center" }}>
        <div style={{ fontSize: "3rem" }}>{online ? "⚠️" : "📡"}</div>
        <h2 style={{ marginTop: 0 }}>{t("session_unavailable.title")}</h2>
        <p className="muted">
          {online
            ? t("session_unavailable.body")
            : t("session_unavailable.body_offline")}
        </p>
        {cachedUser?.display_name && (
          <p style={{ fontWeight: 600 }}>
            {t("session_unavailable.signed_in_as", {
              name: cachedUser.display_name,
            })}
          </p>
        )}
        <button
          type="button"
          className="btn btn-block"
          onClick={() => void retrySession()}
          disabled={retrying}
        >
          {retrying ? t("session_unavailable.retrying") : t("common.retry")}
        </button>
      </div>

      {/* Escape hatch. Without it, a permanently unreachable backend (a
          moved API URL, a decommissioned local install) would trap the
          user on this screen with no way back to the login form. It is
          deliberately the secondary action, under an explicit warning:
          for a guest session this is the irreversible step. */}
      <div className="card" style={{ marginTop: 16 }}>
        <p className="muted" style={{ marginTop: 0 }}>
          {t("session_unavailable.sign_out_intro")}
        </p>
        <div
          className="form-error"
          style={{ background: "var(--surface-2)", color: "var(--text-soft)" }}
        >
          {t("session_unavailable.sign_out_warning")}
        </div>
        <button
          type="button"
          className="btn btn-secondary btn-block"
          onClick={logout}
        >
          {t("session_unavailable.sign_out")}
        </button>
      </div>
    </div>
  );
}

export function ProtectedRoute({ children }: { children: ReactNode }) {
  const { t } = useTranslation();
  const { user, status } = useAuth();
  if (status === "loading") return <div className="page-loading">{t("common.loading")}</div>;
  // A session we couldn't verify is NOT a logged-out session. Redirecting
  // to /login here is what let a transient backend blip turn into a
  // duplicate account and an orphaned one.
  if (status === "unverified") return <SessionUnavailableScreen />;
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}
