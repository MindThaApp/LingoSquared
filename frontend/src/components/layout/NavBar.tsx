import { NavLink } from "react-router-dom";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useAuth } from "../../auth/AuthContext";
import { ProgressApi } from "../../api/endpoints";
import { LanguageSwitcher } from "../LanguageSwitcher";

const TABS = [
  { to: "/", labelKey: "nav.home", icon: "🏠" },
  { to: "/courses", labelKey: "nav.learn", icon: "📚" },
  { to: "/practice", labelKey: "nav.practice", icon: "⚡" },
  { to: "/review", labelKey: "nav.review", icon: "🔁" },
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
          Lingo²
        </NavLink>
        <nav className="topbar-links">
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
            <span className="stat-flame" title={t("nav.day_streak")}>
              🔥 {streak}
            </span>
          )}
          {xp !== null && (
            <span className="stat-xp" title={t("nav.total_xp")}>
              ⭐ {xp}
            </span>
          )}
          <LanguageSwitcher />
        </div>
      </header>
      <nav className="tabbar">
        {TABS.map((tab) => (
          <NavLink
            key={tab.to}
            to={tab.to}
            end={tab.to === "/"}
            className={({ isActive }) => (isActive ? "active" : "")}
          >
            <span className="tab-icon">{tab.icon}</span>
            {t(tab.labelKey)}
          </NavLink>
        ))}
      </nav>
    </>
  );
}
