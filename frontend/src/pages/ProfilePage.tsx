import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { AuthApi, ProgressApi } from "@lingo/shared/api/endpoints";
import { ApiError } from "@lingo/shared/api/client";
import { isGuestUser, useAuth } from "../auth/AuthContext";
import { setAccountDeletedNotice } from "../lib/accountDeletedNotice";
import { VoiceSettings } from "../components/VoiceSettings";
import { SpeechSpeedSettings } from "../components/SpeechSpeedSettings";
import { NotificationSettings } from "../components/NotificationSettings";
import { DeleteAccountConfirm } from "../components/DeleteAccountConfirm";

export function ProfilePage() {
  const { t } = useTranslation();
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const isGuest = isGuestUser(user);
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);

  async function handleDownloadData() {
    setExporting(true);
    setExportError(null);
    try {
      const data = await AuthApi.exportData();
      // Standard vanilla download: serialize to a Blob, mint an object URL,
      // click a synthetic anchor. No library needed, works in every
      // supported browser.
      const blob = new Blob([JSON.stringify(data, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `lingosquared-export-${new Date().toISOString().slice(0, 10)}.json`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      // 401 means the session expired — apiFetch's unauthorized handler has
      // already logged us out, nothing to show here. Anything else: say so
      // and let the user retry.
      setExportError(
        err instanceof ApiError && err.status !== 401
          ? err.message
          : t("profile.export_error"),
      );
    } finally {
      setExporting(false);
    }
  }

  async function handleDeleteAccount() {
    setDeleting(true);
    setDeleteError(null);
    try {
      await AuthApi.deleteAccount();
      // The account is gone server-side; clear the (now-dangling) local
      // session and land on the login page with a one-time confirmation
      // notice. The notice travels via sessionStorage, not route state —
      // see accountDeletedNotice.ts for why route state gets clobbered
      // here.
      setAccountDeletedNotice();
      logout();
      navigate("/login", { replace: true });
    } catch (err) {
      // 401 means the session already expired — apiFetch has fired the
      // unauthorized handler (logging us out), so there's nothing to show
      // here; any other failure means the account still exists, so say so
      // honestly and let the user retry.
      setDeleteError(
        err instanceof ApiError && err.status !== 401
          ? err.message
          : t("profile.delete_error"),
      );
      setDeleting(false);
    }
  }
  const progressQuery = useQuery({ queryKey: ["progress"], queryFn: ProgressApi.progress });
  const streakQuery = useQuery({ queryKey: ["streak"], queryFn: ProgressApi.streak });
  const xpQuery = useQuery({ queryKey: ["xp"], queryFn: ProgressApi.xp });
  const achievementsQuery = useQuery({
    queryKey: ["achievements"],
    queryFn: ProgressApi.achievements,
  });

  return (
    <div>
      <div className="home-hero">
        <h1>{user?.display_name || user?.email}</h1>
      </div>

      {isGuest && (
        <div className="form-error" style={{ background: "var(--surface-2)", color: "var(--text-soft)" }}>
          {t("profile.guest_notice")}
        </div>
      )}

      <div className="stat-grid">
        <div className="stat-card">
          <span className="stat-value">⭐ {xpQuery.data?.total_xp ?? "—"}</span>
          <span className="stat-label">{t("profile.total_xp")}</span>
        </div>
        <div className="stat-card">
          <span className="stat-value">🔥 {streakQuery.data?.streak_days ?? "—"}</span>
          <span className="stat-label">{t("profile.day_streak")}</span>
        </div>
        <div className="stat-card">
          <span className="stat-value">{xpQuery.data?.daily_goal ?? "—"}</span>
          <span className="stat-label">{t("profile.daily_goal")}</span>
        </div>
      </div>

      {progressQuery.data && (
        <div className="card">
          <h2 style={{ marginTop: 0 }}>{t("profile.progress")}</h2>
          <p className="muted">
            {t("profile.lessons_completed", {
              completed: progressQuery.data.lessons_completed,
              started: progressQuery.data.lessons_started,
            })}
          </p>
          {progressQuery.data.skill_progress.map((skill) => (
            <div key={skill.course_id} style={{ marginBottom: 10 }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                <span>{t("course_units.lesson_count", { count: skill.completed_lessons })}</span>
                <span className="muted">
                  {t("profile.mastery", { pct: Math.round(skill.mastery * 100) })}
                </span>
              </div>
              <div className="progress-track">
                <div
                  className="progress-fill"
                  style={{ width: `${Math.round(skill.mastery * 100)}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="card">
        <h2 style={{ marginTop: 0 }}>{t("profile.achievements")}</h2>
        {/* Without the error branch, a failed achievements fetch silently
            renders the "no achievements yet" empty state -- misleading for a
            user who has earned some. */}
        {achievementsQuery.isError ? (
          <div className="feedback-banner error">
            <p style={{ margin: "0 0 10px" }}>{t("profile.achievements_fetch_error")}</p>
            <button className="btn btn-block" onClick={() => achievementsQuery.refetch()}>
              {t("common.retry")}
            </button>
          </div>
        ) : achievementsQuery.data?.length ? (
          achievementsQuery.data.map((achievement) => (
            <div key={achievement.id} style={{ marginBottom: 8, opacity: achievement.earned ? 1 : 0.4 }}>
              <span className="badge">🏅 {achievement.title}</span>{" "}
              <span className="muted" style={{ fontSize: "0.85rem" }}>
                {achievement.description}
              </span>
            </div>
          ))
        ) : (
          <p className="muted">{t("profile.no_achievements")}</p>
        )}
      </div>

      <NotificationSettings />
      <SpeechSpeedSettings />
      <VoiceSettings />

      <button className="btn btn-secondary btn-block" onClick={logout} style={{ marginTop: 8 }}>
        {t("profile.logout")}
      </button>

      {/* Data export lives directly above account deletion on purpose:
          export-before-delete is the natural flow, and deletion below is
          one click away and irreversible. */}
      <div className="card" style={{ marginTop: 16 }}>
        <h2 style={{ marginTop: 0 }}>{t("profile.export_title")}</h2>
        <p className="muted">{t("profile.export_body")}</p>
        {exportError && <div className="form-error">{exportError}</div>}
        <button
          type="button"
          className="btn btn-secondary btn-block"
          disabled={exporting}
          onClick={handleDownloadData}
        >
          {exporting ? t("profile.export_downloading") : t("profile.download_data")}
        </button>
      </div>

      <div className="card" style={{ borderColor: "var(--incorrect)", marginTop: 16 }}>
        <h2 style={{ marginTop: 0, color: "var(--incorrect)" }}>{t("profile.danger_title")}</h2>
        <p className="muted">{t("profile.danger_body")}</p>
        <button
          type="button"
          className="btn btn-danger-soft btn-block"
          onClick={() => {
            setDeleteError(null);
            setDeleteConfirmOpen(true);
          }}
        >
          {t("profile.delete_account")}
        </button>
      </div>

      {deleteConfirmOpen && user && (
        <DeleteAccountConfirm
          email={user.email}
          isGuest={isGuest}
          deleting={deleting}
          error={deleteError}
          onCancel={() => setDeleteConfirmOpen(false)}
          onConfirm={handleDeleteAccount}
        />
      )}
    </div>
  );
}
