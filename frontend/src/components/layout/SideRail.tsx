import { Link, NavLink, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "../../auth/AuthContext";
import { learnPath } from "../../lib/activeCourse";
import { NAV_TABS } from "./navTabs";

// Desktop-only (>= 1024px) left navigation rail. Rendered at every width but
// hidden by CSS below 1024px so phones/tablets are unchanged. Same
// destinations as NavBar; NavLink sets aria-current="page" on the active link.
export function SideRail() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const { pathname } = useLocation();
  if (!user) return null;
  const tabs = NAV_TABS.map((tab) => (tab.to === "/courses" ? { ...tab, to: learnPath(user.id) } : tab));
  return (
    <nav className="side-rail" aria-label={t("nav.main_nav")}>
      <Link to="/" className="side-rail-brand">
        Auvel
      </Link>
      <div className="side-rail-links">
        {tabs.map((tab) => (
          <NavLink
            key={tab.labelKey}
            to={tab.to}
            end={tab.to === "/"}
            className={({ isActive }) =>
              isActive || (tab.labelKey === "nav.learn" && pathname.startsWith("/courses")) ? "active" : ""
            }
          >
            <span className="side-rail-icon" aria-hidden="true">
              {tab.icon}
            </span>
            <span>{t(tab.labelKey)}</span>
          </NavLink>
        ))}
      </div>
    </nav>
  );
}
