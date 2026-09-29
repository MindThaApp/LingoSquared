import "@testing-library/jest-dom/vitest";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { I18nextProvider } from "react-i18next";
import type { ReactNode } from "react";
import i18n from "../i18n";
import { expectNoSeriousA11yViolations } from "../test/axe";

// Web Storage shim (Node's experimental globals shadow jsdom's — see
// AuthContext.test.tsx for the full why).
class MemoryStorage {
  private data = new Map<string, string>();
  get length() {
    return this.data.size;
  }
  clear() {
    this.data.clear();
  }
  getItem(key: string) {
    return this.data.has(key) ? this.data.get(key)! : null;
  }
  key(index: number) {
    return Array.from(this.data.keys())[index] ?? null;
  }
  removeItem(key: string) {
    this.data.delete(key);
  }
  setItem(key: string, value: string) {
    this.data.set(key, String(value));
  }
}
for (const name of ["localStorage", "sessionStorage"] as const) {
  if (!globalThis[name]) {
    Object.defineProperty(globalThis, name, {
      value: new MemoryStorage() as unknown as Storage,
      configurable: true,
      writable: true,
    });
  }
}

const { user, course, mcItem, authState } = vi.hoisted(() => {
const user = {
  id: "u1",
  email: "learner@example.com",
  display_name: "Sam",
  is_admin: false,
};

const course = {
  id: "c1",
  source_language: "en",
  target_language: "nl",
  title: "English to Dutch",
  level: "A1",
  unit_count: 3,
  description: "Learn Dutch from scratch.",
};

const mcItem = {
  id: "p1",
  type: "multiple_choice",
  prompt: {
    text_blocks: [{ text: "Choose the Dutch word for 'hello'.", language_code: "en", direction: "ltr" }],
    options: ["hallo", "tot ziens", "dank je", "alsjeblieft"],
    answer_language_code: "nl",
  },
};

  // LoginPage/RegisterPage redirect an authenticated user away, so those two
  // tests flip this to "unauthenticated".
  const authState = { status: "authenticated" as "authenticated" | "unauthenticated" };

  return { user, course, mcItem, authState };
});

vi.mock("../auth/AuthContext", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../auth/AuthContext")>();
  return {
    ...actual,
    useAuth: () => ({
      user: authState.status === "authenticated" ? user : null,
      status: authState.status,
      loading: false,
      retrying: false,
      retrySession: vi.fn(),
      login: vi.fn(),
      register: vi.fn(),
      continueAsGuest: vi.fn(),
      logout: vi.fn(),
    }),
  };
});

vi.mock("@lingo/shared/api/endpoints", () => {
  const streak = {
    streak_days: 4,
    last_activity_date: "2026-09-28",
    streak_freezes_available: 1,
    freeze_used_today: false,
    active_today: false,
  };
  const progress = {
    lessons_started: 3,
    lessons_completed: 2,
    lesson_progress: [
      { lesson_id: "l1", started_at: "2026-09-01", completed_at: null, accuracy: null, xp_earned: null },
    ],
    skill_progress: [{ course_id: "c1", completed_lessons: 2, mastery: 0.4 }],
    vocabulary_progress: [],
    grammar_progress: [],
  };
  return {
    AuthApi: { exportData: vi.fn(), deleteAccount: vi.fn(), login: vi.fn(), register: vi.fn() },
    ProgressApi: {
      streak: vi.fn().mockResolvedValue(streak),
      xp: vi.fn().mockResolvedValue({ total_xp: 120, daily_goal: 20, xp_today: 10 }),
      progress: vi.fn().mockResolvedValue(progress),
      achievements: vi.fn().mockResolvedValue([
        { id: "a1", code: "first", title: "First lesson", description: "Finish a lesson", earned: true },
        { id: "a2", code: "week", title: "Week streak", description: "7 days in a row", earned: false },
      ]),
      quests: vi.fn().mockResolvedValue({
        quests: [
          { code: "q1", title: "Earn 20 XP", description: "Keep learning", xp_reward: 5, completed: false, progress: 10, target: 20 },
          { code: "q2", title: "One lesson", description: "Finish a lesson", xp_reward: 5, completed: true, progress: 1, target: 1 },
        ],
      }),
    },
    ReviewApi: {
      due: vi.fn().mockResolvedValue({ due_count: 4, by_course: [{ course_id: "c1", due_count: 4 }] }),
      session: vi.fn().mockResolvedValue({ items: [mcItem] }),
      answer: vi.fn().mockResolvedValue({ correct: false, result: "incorrect", correct_response: "hallo", xp_awarded: 0 }),
      retry: vi.fn(),
      reportIssue: vi.fn(),
    },
    CatalogApi: {
      languages: vi.fn().mockResolvedValue([
        { code: "en", name: "English", native_name: "English", script: "latin", direction: "ltr" },
        { code: "nl", name: "Dutch", native_name: "Nederlands", script: "latin", direction: "ltr" },
      ]),
      course: vi.fn().mockResolvedValue(course),
      units: vi.fn().mockResolvedValue([
        { id: "un1", title: "Greetings", order: 1, lesson_count: 3, completed_lesson_count: 3, section: "reading_writing", locked: false, checkpoint_passed: true, content_key: "nl.a1.unit01.greetings" },
        { id: "un2", title: "Family", order: 2, lesson_count: 3, completed_lesson_count: 1, section: "reading_writing", locked: false, checkpoint_passed: false, content_key: "nl.a1.unit02.family" },
        { id: "un3", title: "Food", order: 3, lesson_count: 3, completed_lesson_count: 0, section: "reading_writing", locked: true, checkpoint_passed: false, content_key: "nl.a1.unit03.food" },
        { id: "un4", title: "Say it aloud", order: 4, lesson_count: 2, completed_lesson_count: 0, section: "speaking", locked: false, checkpoint_passed: false, content_key: null },
      ]),
    },
    PracticeApi: {
      batch: vi.fn().mockResolvedValue({ locked: false, items: [mcItem] }),
      answer: vi.fn().mockResolvedValue({ correct: true, result: "correct", correct_response: "hallo", xp_awarded: 5 }),
      reportIssue: vi.fn(),
    },
    PushApi: {
      vapidPublicKey: vi.fn().mockResolvedValue({ public_key: null, configured: false }),
      subscribe: vi.fn(),
      unsubscribe: vi.fn(),
    },
  };
});

import { HomePage } from "./HomePage";
import { CourseUnitsPage } from "./CourseUnitsPage";
import { ReviewPage } from "./ReviewPage";
import { PracticeFeedPage } from "./PracticeFeedPage";
import { ProfilePage } from "./ProfilePage";
import { LoginPage } from "./LoginPage";
import { RegisterPage } from "./RegisterPage";
import { ConversationRunner } from "../components/ConversationRunner";
import { NavBar } from "../components/layout/NavBar";

function wrap(ui: ReactNode, route = "/") {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <I18nextProvider i18n={i18n}>
        <MemoryRouter initialEntries={[route]}>{ui}</MemoryRouter>
      </I18nextProvider>
    </QueryClientProvider>,
  );
}

// Mirrors App.tsx's shell: the nav + <main> landmark around each page.
function Shell({ children }: { children: ReactNode }) {
  return (
    <div className="app">
      <NavBar />
      <main className="app-main">{children}</main>
    </div>
  );
}

describe("learner-flow pages have no serious/critical axe violations", { timeout: 30_000 }, () => {
  beforeEach(() => {
    localStorage.clear();
    authState.status = "authenticated";
  });

  it("app shell / nav", async () => {
    const { container } = wrap(<Shell><div /></Shell>);
    await screen.findByText(/🔥 4/);
    await expectNoSeriousA11yViolations(container);
  });

  it("HomePage", async () => {
    const { container } = wrap(<Shell><HomePage /></Shell>);
    await screen.findAllByText("Earn 20 XP");
    await expectNoSeriousA11yViolations(container);
  });

  it("CourseUnitsPage", async () => {
    const { container } = wrap(
      <Shell>
        <Routes>
          <Route path="/courses/:courseId" element={<CourseUnitsPage />} />
        </Routes>
      </Shell>,
      "/courses/c1",
    );
    await screen.findByText("Family");
    fireEvent.click(await screen.findByRole("button", { name: /unit index/i }));
    await expectNoSeriousA11yViolations(container);
  });

  it("ReviewPage (exercise + graded incorrect)", async () => {
    const { container } = wrap(<Shell><ReviewPage /></Shell>);
    fireEvent.click(await screen.findByText("hallo"));
    fireEvent.click(screen.getByRole("button", { name: i18n.t("common.check") }));
    await screen.findByText(i18n.t("review.try_again"));
    await expectNoSeriousA11yViolations(container);
  });

  it("PracticeFeedPage (graded correct)", async () => {
    const { container } = wrap(<Shell><PracticeFeedPage /></Shell>);
    fireEvent.click(await screen.findByText("hallo"));
    fireEvent.click(screen.getByRole("button", { name: i18n.t("common.check") }));
    await screen.findByText("+5 XP");
    await expectNoSeriousA11yViolations(container);
  });

  it("ProfilePage", async () => {
    const { container } = wrap(<Shell><ProfilePage /></Shell>);
    await screen.findByText(/First lesson/);
    await expectNoSeriousA11yViolations(container);
  });

  it("ProfilePage with browser voices available (voice selects)", async () => {
    const voices = [{ name: "Xander", lang: "nl-NL", voiceURI: "xander" }];
    Object.defineProperty(window, "speechSynthesis", {
      configurable: true,
      value: {
        getVoices: () => voices,
        addEventListener: () => {},
        removeEventListener: () => {},
        cancel: () => {},
        speak: () => {},
      },
    });
    try {
      const { container, unmount } = wrap(<Shell><ProfilePage /></Shell>);
      await screen.findByText(/First lesson/);
      await screen.findByRole("combobox", { name: "Nederlands" });
      await expectNoSeriousA11yViolations(container);
      unmount();
    } finally {
      delete (window as unknown as Record<string, unknown>).speechSynthesis;
    }
  });

  it("ProfilePage delete-account dialog", async () => {
    const { container } = wrap(<Shell><ProfilePage /></Shell>);
    await screen.findByText(/First lesson/);
    fireEvent.click(screen.getByRole("button", { name: i18n.t("profile.delete_account") }));
    await screen.findByRole("dialog");
    await expectNoSeriousA11yViolations(container);
  });

  it("LoginPage (incl. error + guest form)", async () => {
    authState.status = "unauthenticated";
    const { container } = wrap(<main><LoginPage /></main>, "/login");
    fireEvent.click(await screen.findByRole("button", { name: i18n.t("login.continue_as_guest") }));
    await screen.findByLabelText(i18n.t("login.pick_name"));
    await expectNoSeriousA11yViolations(container);
  });

  it("ConversationRunner", async () => {
    const node = {
      id: "n1",
      app_turn: { text: "Hoe heet je?", language_code: "nl", direction: "ltr" },
      accepted_variants: ["Ik heet Sam"],
      answer_language_code: "nl",
      terminal: false,
    };
    const { container } = wrap(
      <main>
        <ConversationRunner
          itemId="p9"
          prompt={{ start_node_id: "n1", current_node: node, nodes: [node] }}
          onAnswered={() => {}}
        />
      </main>,
    );
    await screen.findByText("Hoe heet je?");
    await expectNoSeriousA11yViolations(container);
  });

  it("RegisterPage", async () => {
    authState.status = "unauthenticated";
    const { container } = wrap(<main><RegisterPage /></main>, "/register");
    await screen.findByLabelText(i18n.t("register.email"));
    await expectNoSeriousA11yViolations(container);
  });

  it("practice feed announces the verdict inside a pre-existing live region", async () => {
    wrap(<Shell><PracticeFeedPage /></Shell>);
    const option = await screen.findByText("hallo");
    // The live region must already be in the DOM (empty) BEFORE grading.
    const region = document.querySelector(".practice-card [role='status']");
    expect(region).not.toBeNull();
    expect(region).toBeEmptyDOMElement();
    fireEvent.click(option);
    fireEvent.click(screen.getByRole("button", { name: i18n.t("common.check") }));
    await waitFor(() => expect(region).not.toBeEmptyDOMElement());
    expect(region!.firstElementChild!.className).toContain("feedback-banner");
    // The banner itself must not be a second (nested) live region.
    expect(region!.querySelector("[role='status']")).toBeNull();
  });

  it("review page announces the verdict inside a pre-existing live region", async () => {
    wrap(<Shell><ReviewPage /></Shell>);
    const option = await screen.findByText("hallo");
    const region = document.querySelector("main [role='status'][aria-live='polite']");
    expect(region).not.toBeNull();
    // The live region must already be in the DOM (empty) BEFORE grading.
    expect(region).toBeEmptyDOMElement();
    fireEvent.click(option);
    fireEvent.click(screen.getByRole("button", { name: i18n.t("common.check") }));
    await waitFor(() => expect(region).not.toBeEmptyDOMElement());
    expect(region!.firstElementChild!.className).toContain("feedback-banner");
    expect(region!.textContent).toContain(i18n.t("review.incorrect"));
    expect(region!.querySelector("[role='status']")).toBeNull();
  });
});
