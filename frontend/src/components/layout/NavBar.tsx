import { NavLink } from "react-router-dom";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useAuth } from "../../auth/AuthContext";
import { ProgressApi } from "@lingo/shared/api/endpoints";
import { LanguageSwitcher } from "../LanguageSwitcher";

const TABS = [
  { to: "/", labelKey: "nav.home", icon: "🏠" },
  { to: "/courses", labelKey: "nav.learn", icon: "📚" },
  { to: "/practice", labelKey: "nav.practice", icon: "⚡" },
  { to: "/review", labelKey: "nav.review", icon: "🔁" },
  { to: "/vocabulary", labelKey: "nav.vocabulary", icon: "🧠" },
  { to: "/profile", labelKey: "nav.profile", icon: "👤" },
];

export function NavBar() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const [streak, setStreak] = useState<number | null>(null);
  const [xp, setXp] = useState<number | null>(null);

  useEffect(() => {
    if (!user) return;
    ProgressApi.streak().then((s) => setStreak(s.streak_days)).catch(() => {});
    ProgressApi.xp().then((x) => setXp(x.total_xp)).catch(() => {});
  }, [user]);

  if (!user) return null;

  return (
    <>
      <header className="topbar">
        <NavLink to="/" className="topbar-brand">
          Auvel
        </NavLink>
        <nav className="topbar-links" aria-label={t("nav.main_label")}>
          {TABS.map((tab) => (
            <NavLink
              key={tab.to}
              to={tab.to}
              end={tab.to === "/"}
              className={({ isActive }) => (isActive ? "active" : "")}
            >
              {t(tab.labelKey)}
            </NavLink>
          ))}
        </nav>
        <div className="topbar-stats">
          {streak !== null && (
            <span
              className="stat-flame"
              title={t("nav.day_streak")}
              role="img"
              aria-label={`${t("nav.day_streak")}: ${streak}`}
            >
              🔥 {streak}
            </span>
          )}
          {xp !== null && (
            <span
              className="stat-xp"
              title={t("nav.total_xp")}
              role="img"
              aria-label={`${t("nav.total_xp")}: ${xp}`}
            >
              ⭐ {xp}
            </span>
          )}
          <LanguageSwitcher />
        </div>
      </header>
      <nav className="tabbar" aria-label={t("nav.tabs_label")}>
        {TABS.map((tab) => (
          <NavLink
            key={tab.to}
            to={tab.to}
            end={tab.to === "/"}
            className={({ isActive }) => (isActive ? "active" : "")}
          >
            <span className="tab-icon" aria-hidden="true">
              {tab.icon}
            </span>
            {t(tab.labelKey)}
          </NavLink>
        ))}
      </nav>
    </>
  );
}
