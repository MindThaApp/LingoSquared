import { describe, expect, it, vi, beforeEach } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (k: string, o?: { xp?: number }) => (o?.xp !== undefined ? `${k}:${o.xp}` : k),
  }),
}));
vi.mock("@lingo/shared/api/endpoints", () => ({
  ProgressApi: {
    xp: vi.fn(),
    setDailyGoal: vi.fn(),
  },
}));

import { ProgressApi } from "@lingo/shared/api/endpoints";
import { DailyGoalPicker } from "./DailyGoalPicker";

function renderPicker() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <DailyGoalPicker />
    </QueryClientProvider>,
  );
}

describe("DailyGoalPicker", () => {
  beforeEach(() => {
    vi.mocked(ProgressApi.xp).mockResolvedValue({ total_xp: 0, daily_goal: 20, xp_today: 0 } as never);
    vi.mocked(ProgressApi.setDailyGoal).mockReset().mockResolvedValue({ daily_goal_xp: 30 });
  });

  it("marks the current goal and saves a new one", async () => {
    renderPicker();
    const radios = await screen.findAllByRole("radio");
    expect(radios).toHaveLength(4);
    await waitFor(() => expect(radios[1].getAttribute("aria-checked")).toBe("true"));
    fireEvent.click(radios[2]);
    await waitFor(() => expect(ProgressApi.setDailyGoal).toHaveBeenCalledWith(30));
    expect(await screen.findByText("profile.goal_saved")).toBeTruthy();
  });

  it("shows an error when saving fails", async () => {
    vi.mocked(ProgressApi.setDailyGoal).mockRejectedValue(new Error("x"));
    renderPicker();
    const radios = await screen.findAllByRole("radio");
    await waitFor(() => expect(radios[1].getAttribute("aria-checked")).toBe("true"));
    fireEvent.click(radios[3]);
    expect(await screen.findByRole("alert")).toBeTruthy();
  });
});
