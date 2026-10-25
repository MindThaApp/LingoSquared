import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { sendProblemReport } from "../lib/sentry";

const MAX_MESSAGE = 2000;

// "Report a problem": an explicit, learner-initiated report, so it is sent
// regardless of the crash-report setting.
export function ReportProblem() {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const [message, setMessage] = useState("");
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<"idle" | "sending" | "sent" | "error">("idle");

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!message.trim()) return;
    setStatus("sending");
    try {
      await sendProblemReport({ message: message.trim(), email });
      setStatus("sent");
      setMessage("");
      setEmail("");
    } catch {
      setStatus("error");
    }
  }

  return (
    <div className="card" style={{ marginTop: 16 }}>
      <h2 style={{ marginTop: 0 }}>{t("report_problem.title")}</h2>
      {status === "sent" ? (
        <p role="status">{t("report_problem.thanks")}</p>
      ) : !open ? (
        <>
          <p className="muted">{t("report_problem.hint")}</p>
          <button type="button" className="btn btn-secondary" onClick={() => setOpen(true)}>
            {t("report_problem.open")}
          </button>
        </>
      ) : (
        <form onSubmit={handleSubmit}>
          <div className="form-field">
            <label htmlFor="report-problem-message">{t("report_problem.message_label")}</label>
            <textarea
              id="report-problem-message"
              rows={4}
              required
              maxLength={MAX_MESSAGE}
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder={t("report_problem.message_placeholder")}
            />
          </div>
          <div className="form-field">
            <label htmlFor="report-problem-email">{t("report_problem.email_label")}</label>
            <input
              id="report-problem-email"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
            <small className="muted">{t("report_problem.email_hint")}</small>
          </div>
          {status === "error" && <p role="alert">{t("report_problem.error")}</p>}
          <div style={{ display: "flex", gap: 8 }}>
            <button className="btn" type="submit" disabled={status === "sending" || !message.trim()}>
              {t("report_problem.send")}
            </button>
            <button type="button" className="btn btn-secondary" onClick={() => setOpen(false)}>
              {t("common.cancel")}
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
