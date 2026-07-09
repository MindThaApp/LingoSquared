import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";

export function NotFoundPage() {
  const { t } = useTranslation();
  return (
    <div className="card" style={{ textAlign: "center", marginTop: 40 }}>
      <div style={{ fontSize: "3rem" }}>🧭</div>
      <h2>{t("not_found.title")}</h2>
      <p className="muted">{t("not_found.body")}</p>
      <Link className="btn" to="/">
        {t("not_found.back_home")}
      </Link>
    </div>
  );
}
