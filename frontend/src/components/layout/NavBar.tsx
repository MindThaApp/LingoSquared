import { NavLink, useLocation } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { useAuth } from "../../auth/AuthContext";
import { ProgressApi } from "@lingo/shared/api/endpoints";
import { LanguageSwitcher } from "../LanguageSwitcher";
import { learnPath } from "../../lib/activeCourse";
import { NAV_TABS } from "./navTabs";
import { SideRail } from "./SideRail";

export function NavBar() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const { pathname } = useLocation();
  // Same keys/fetchers as HomePage so the cache is shared and invalidation
  // after an answer/lesson refreshes the top bar too.
  const streakQuery = useQuery({
    queryKey: ["streak"],
    queryFn: ProgressApi.streak,
    enabled: !!user,
  });
  const xpQuery = useQuery({ queryKey: ["xp"], queryFn: ProgressApi.xp, enabled: !!user });
  const streak = streakQuery.data?.streak_days ?? null;
  const xp = xpQuery.data?.total_xp ?? null;

  if (!user) return null;

  // Learn resumes the active course (per user, per device) when one is set.
  const tabs = NAV_TABS.map((tab) => (tab.to === "/courses" ? { ...tab, to: learnPath(user.id) } : tab));

  return (
    <>
      <SideRail />
      <header className="topbar">
        <NavLink to="/" className="topbar-brand">
          Auvel
        </NavLink>
        <nav className="topbar-links">
          {tabs.map((tab) => (
            <NavLink
              key={tab.to}
              to={tab.to}
              end={tab.to === "/"}
              className={({ isActive }) =>
              isActive || (tab.labelKey === "nav.learn" && pathname.startsWith("/courses")) ? "active" : ""
            }
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
        {tabs.map((tab) => (
          <NavLink
            key={tab.to}
            to={tab.to}
            end={tab.to === "/"}
            className={({ isActive }) =>
              isActive || (tab.labelKey === "nav.learn" && pathname.startsWith("/courses")) ? "active" : ""
            }
          >
            <span className="tab-icon">{tab.icon}</span>
            {t(tab.labelKey)}
          </NavLink>
        ))}
      </nav>
    </>
  );
}
