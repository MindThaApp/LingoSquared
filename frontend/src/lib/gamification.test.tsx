import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { GamificationState } from "@lingo/shared/api/types";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (k: string, o?: Record<string, unknown>) => (o ? `${k}:${JSON.stringify(o)}` : k),
  }),
}));
vi.mock("../auth/AuthContext", () => ({ useOptionalAuth: () => ({ user: { id: "u1" } }) }));
vi.mock("@lingo/shared/api/gamification", () => ({
  GamificationApi: {
    state: vi.fn(),
    restoreHeart: vi.fn(),
    spend: vi.fn(),
    leaderboard: vi.fn(),
    setLeaderboardOptOut: vi.fn(),
  },
}));

import { GamificationApi } from "@lingo/shared/api/gamification";
import { formatCountdown } from "./gamification";
import { HeartsBadge } from "../components/HeartsBadge";
import { OutOfHearts } from "../components/OutOfHearts";
import { GamificationSettings } from "../components/GamificationSettings";
import { LeaderboardPage } from "../pages/LeaderboardPage";

const baseState = (over: Partial<GamificationState> = {}): GamificationState => ({
  hearts: { enabled: true, hearts: 3, max_hearts: 5, next_heart_at: null, refill_seconds: 14400 },
  gems: { enabled: true, balance: 25, costs: { heart_refill: 10, streak_freeze: 20 } },
  leaderboard: { enabled: true, opted_out: false },
  ...over,
});

function wrap(ui: React.ReactElement) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.mocked(GamificationApi.state).mockReset().mockResolvedValue(baseState());
  vi.mocked(GamificationApi.spend).mockReset();
  vi.mocked(GamificationApi.leaderboard).mockReset();
  vi.mocked(GamificationApi.setLeaderboardOptOut).mockReset().mockResolvedValue({ opted_out: true });
});

describe("formatCountdown", () => {
  const now = Date.parse("2026-01-01T00:00:00Z");
  it("formats hours/minutes, rounds up, and handles past/null", () => {
    expect(formatCountdown("2026-01-01T02:15:00Z", now)).toBe("2h 15m");
    expect(formatCountdown("2026-01-01T00:12:10Z", now)).toBe("13m");
    expect(formatCountdown("2025-12-31T23:00:00Z", now)).toBe("<1m");
    expect(formatCountdown(null, now)).toBeNull();
  });
});

describe("HeartsBadge", () => {
  it("shows hearts when the server has them on", async () => {
    wrap(<HeartsBadge />);
    expect(await screen.findByRole("img")).toBeTruthy();
    expect(screen.getByRole("img").getAttribute("aria-label")).toContain("gamification.hearts_label");
  });
  it("renders nothing when hearts are off", async () => {
    vi.mocked(GamificationApi.state).mockResolvedValue(
      baseState({ hearts: { enabled: false, hearts: 5, max_hearts: 5, next_heart_at: null, refill_seconds: 14400 } }),
    );
    const { container } = wrap(<HeartsBadge />);
    await waitFor(() => expect(GamificationApi.state).toHaveBeenCalled());
    expect(container.querySelector("[role=img]")).toBeNull();
  });
});

describe("OutOfHearts", () => {
  it("offers practice and review instead of a dead end, and refills with gems", async () => {
    vi.mocked(GamificationApi.spend).mockResolvedValue({ applied: true, item: "heart_refill", cost: 10, gem_balance: 15 });
    const onRefilled = vi.fn();
    wrap(<OutOfHearts onBack={() => {}} onRefilled={onRefilled} />);
    expect(screen.getByText("gamification.practice_instead").getAttribute("href")).toBe("/practice");
    expect(screen.getByText("gamification.review_instead").getAttribute("href")).toBe("/review");
    const refill = await screen.findByRole("button", { name: /gamification\.refill_with_gems/ });
    await waitFor(() => expect((refill as HTMLButtonElement).disabled).toBe(false));
    fireEvent.click(refill);
    await waitFor(() => expect(onRefilled).toHaveBeenCalled());
    expect(GamificationApi.spend).toHaveBeenCalledWith("heart_refill");
  });
  it("disables the refill when gems are short", async () => {
    vi.mocked(GamificationApi.state).mockResolvedValue(
      baseState({ gems: { enabled: true, balance: 2, costs: { heart_refill: 10, streak_freeze: 20 } } }),
    );
    wrap(<OutOfHearts onBack={() => {}} />);
    const refill = await screen.findByRole("button", { name: /gamification\.refill_with_gems/ });
    await waitFor(() => expect((refill as HTMLButtonElement).disabled).toBe(true));
  });
});

describe("GamificationSettings", () => {
  it("hides itself when gems and leaderboard are both off", async () => {
    vi.mocked(GamificationApi.state).mockResolvedValue(
      baseState({ gems: { enabled: false, balance: 0, costs: {} }, leaderboard: { enabled: false, opted_out: false } }),
    );
    const { container } = wrap(<GamificationSettings />);
    await waitFor(() => expect(GamificationApi.state).toHaveBeenCalled());
    expect(container.querySelector("[data-testid=gamification-settings]")).toBeNull();
  });
  it("lets the learner opt out of the leaderboard", async () => {
    wrap(<GamificationSettings />);
    const box = (await screen.findByRole("checkbox")) as HTMLInputElement;
    expect(box.checked).toBe(true);
    fireEvent.click(box);
    await waitFor(() => expect(GamificationApi.setLeaderboardOptOut).toHaveBeenCalledWith(true));
  });
});

describe("LeaderboardPage", () => {
  it("lists entries, marks me, shows only display names", async () => {
    vi.mocked(GamificationApi.leaderboard).mockResolvedValue({
      week_start: "2026-01-05T00:00:00Z",
      week_end: "2026-01-12T00:00:00Z",
      opted_out: false,
      entries: [
        { rank: 1, display_name: "Bob", xp: 40, is_me: false },
        { rank: 2, display_name: "Alice", xp: 15, is_me: true },
      ],
      me: { rank: 2, xp: 15 },
    });
    wrap(<LeaderboardPage />);
    expect(await screen.findByText(/Bob/)).toBeTruthy();
    const me = screen.getByText(/Alice/).closest("li");
    expect(me?.getAttribute("aria-current")).toBe("true");
    expect(screen.getByText(/gamification\.leaderboard_your_rank/)).toBeTruthy();
  });
  it("shows the opted-out note and an unavailable message when the flag is off", async () => {
    vi.mocked(GamificationApi.leaderboard).mockResolvedValue({
      week_start: "", week_end: "", opted_out: true, entries: [], me: null,
    });
    wrap(<LeaderboardPage />);
    expect(await screen.findByText(/gamification\.leaderboard_opted_out/)).toBeTruthy();
  });
  it("says unavailable when the server flag is off", async () => {
    vi.mocked(GamificationApi.state).mockResolvedValue(
      baseState({ leaderboard: { enabled: false, opted_out: false } }),
    );
    wrap(<LeaderboardPage />);
    expect(await screen.findByText("gamification.leaderboard_unavailable")).toBeTruthy();
    expect(GamificationApi.leaderboard).not.toHaveBeenCalled();
  });
});
