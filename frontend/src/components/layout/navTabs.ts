// Shared by NavBar (top links + bottom tab bar) and SideRail (desktop left
// rail) so the destinations/labels/icons can never drift apart.
//
// `phone: false` keeps a destination out of the 5-slot bottom tab bar. Words
// is the least-used destination (a browse list, not a daily action), so on
// phones it is reached from a card on Profile; desktop nav still lists it.
export interface NavTab {
  to: string;
  labelKey: string;
  icon: string;
  phone: boolean;
}

export const NAV_TABS: NavTab[] = [
  { to: "/", labelKey: "nav.home", icon: "home", phone: true },
  { to: "/courses", labelKey: "nav.learn", icon: "learn", phone: true },
  { to: "/practice", labelKey: "nav.practice", icon: "practice", phone: true },
  { to: "/review", labelKey: "nav.review", icon: "review", phone: true },
  { to: "/vocabulary", labelKey: "nav.vocabulary", icon: "vocabulary", phone: false },
  { to: "/profile", labelKey: "nav.profile", icon: "profile", phone: true },
];
