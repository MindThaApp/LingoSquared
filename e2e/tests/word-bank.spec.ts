import { test, expect } from "@playwright/test";
import { enBlock, mockedApp, openLessonViaCourseMap, reply, unit, type LessonFixture } from "./mocks";

// Beginner (A1/A2) tap-to-build word bank on free-text items
// (frontend/src/components/exercises/WordBankInput.tsx via AnswerModeSwitch).
// Fully route-mocked -- see tests/mocks.ts. Tiles are shuffled for display
// (lib/wordBankTiles.ts), so every tile is selected by its TEXT, never by
// position.

const ANSWER = "Ik drink water";

for (const type of ["translation", "writing_prompt"] as const) {
  test(`${type} with prompt.word_bank: tap to build, tap to remove, Check sends the built string`, async ({ page, baseURL }) => {
    const exerciseId = `ex-${type}`;
    const lesson: LessonFixture = {
      id: "lesson-wb",
      unit_id: "unit-1",
      title: "Drinks",
      teaching: [],
      exercises: [
        {
          id: exerciseId,
          type,
          order: 1,
          prompt: {
            text_blocks: [enBlock("I drink water")],
            answer_language_code: "nl",
            // Answer tokens + distractors, exactly as the compiler emits them.
            word_bank: ["Ik", "drink", "water", "melk", "jij"],
          },
        },
      ],
    };
    const api = await mockedApp(page, baseURL, {
      units: [unit({ id: "unit-1", title: "Basics 1", order: 1, track: "core", content_key: "nl.a1.unit01.basics" })],
      lessons: [lesson],
    });
    api.on("POST", "/exercises/:id/answer", ({ body }) =>
      (body as { response?: unknown })?.response === ANSWER
        ? { correct: true, result: "correct", correct_response: ANSWER, xp_awarded: 10 }
        : reply(500, { error: { code: "unexpected_payload", message: JSON.stringify(body) } }),
    );

    await openLessonViaCourseMap(page, "Basics 1", "Drinks");

    // A1 course -> bank mode by default; typed input is one click away.
    const bank = page.getByTestId("word-bank-tiles");
    const built = page.getByTestId("word-bank-answer");
    await expect(bank.getByRole("button", { name: "melk", exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "Type instead" })).toBeVisible();
    const check = page.getByRole("button", { name: "Check", exact: true });
    await expect(check).toBeDisabled();

    // Build "Ik melk drink water", then pull the wrong "melk" back out.
    for (const word of ["Ik", "melk", "drink", "water"]) {
      await bank.getByRole("button", { name: word, exact: true }).click();
    }
    await expect(built.getByRole("button")).toHaveText(["Ik", "melk", "drink", "water"]);
    // A placed tile leaves an invisible (aria-hidden) placeholder in the bank.
    await expect(bank.getByRole("button", { name: "melk", exact: true })).toHaveCount(0);

    await built.getByRole("button", { name: "melk", exact: true }).click();
    await expect(built.getByRole("button")).toHaveText(["Ik", "drink", "water"]);
    // ...and it is tappable in the bank again.
    await expect(bank.getByRole("button", { name: "melk", exact: true })).toBeVisible();
    await expect(bank.getByRole("button", { name: "melk", exact: true })).toBeEnabled();

    const answerRequest = page.waitForRequest(
      (r) => r.method() === "POST" && new URL(r.url()).pathname === `/exercises/${exerciseId}/answer`,
    );
    await check.click();
    const req = await answerRequest;
    // Answer-payload contract: the same trimmed, space-joined string typing
    // would send, and no input_mode for a tapped (non-spoken) answer.
    expect(req.postDataJSON()).toEqual({ response: ANSWER });

    await expect(page.getByRole("status").filter({ hasText: "Correct!" })).toBeVisible();
    await page.getByRole("button", { name: "Continue" }).click();
    await page.waitForURL(`**/lessons/${lesson.id}/done`);
    await expect(page.getByRole("heading", { name: "Lesson complete!" })).toBeVisible();

    expect(api.crashReports).toEqual([]);
  });
}
