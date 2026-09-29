import "@testing-library/jest-dom/vitest";
import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ProgressApi } from "@lingo/shared/api/endpoints";
import { FixMistakes } from "./FixMistakes";

vi.mock("@lingo/shared/api/endpoints", () => ({ ProgressApi: { reviews: vi.fn() } }));
vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string) => k }) }));

function renderIt() {
  const qc = new QueryClient();
  return render(
    <QueryClientProvider client={qc}>
      <FixMistakes />
    </QueryClientProvider>,
  );
}

describe("FixMistakes", () => {
  it("renders nothing for an empty /me/reviews response", async () => {
    vi.mocked(ProgressApi.reviews).mockResolvedValue({ items: [], next_cursor: null });
    const { container } = renderIt();
    await waitFor(() => expect(ProgressApi.reviews).toHaveBeenCalled());
    expect(container).toBeEmptyDOMElement();
  });

  it("renders the card when a due mistake exists", async () => {
    vi.mocked(ProgressApi.reviews).mockResolvedValue({
      items: [
        {
          id: "r1",
          exercise_id: "e1",
          due_at: "2020-01-01T00:00:00Z",
          mastery: 0,
          exercise: { id: "e1", type: "translation", prompt: {} as never },
        },
      ],
      next_cursor: null,
    });
    renderIt();
    expect(await screen.findByText("fix_mistakes.card_title")).toBeInTheDocument();
  });
});
