import { expect, type Page } from "@playwright/test";

/** Never hit real TTS/audio or Sentry from a journey test. */
export async function stubExternals(page: Page): Promise<void> {
  await page.route(/\/(tts|stt)(\/|\?|$)|\/media\/audio\//, (route) =>
    route.fulfill({ status: 204, body: "" }),
  );
  await page.route(/sentry\.io/, (route) => route.fulfill({ status: 200, body: "{}" }));
}

export type Step = { prompt: RegExp; kind: "choice" | "type" | "order"; right: string; wrong: string };

/**
 * Walks one lesson: teaching cards, then exercises until the done page. `wrongFirst` answers the
 * first exercise incorrectly once (the lesson re-queues it). Answers are looked up by prompt text
 * from known fixture content, so this fails loudly if content changes.
 */
export async function runLesson(
  page: Page,
  steps: Step[],
  opts: { wrongFirst?: boolean } = {},
): Promise<{ wrongAnswers: number; rightAnswers: number; prompts: string[] }> {
  // Teaching cards are interleaved with exercises, so each turn handles whichever screen shows.
  const next = page.getByRole("button", { name: /^(Next|Start practice)$/ });
  const shell = page.locator(".exercise-shell");
  const done = page.getByRole("heading", { name: "Lesson complete!" });
  let wrongLeft = opts.wrongFirst ? 1 : 0;
  let wrongAnswers = 0;
  let rightAnswers = 0;
  const prompts: string[] = [];
  for (let i = 0; i < 40; i++) {
    await expect(next.or(shell).or(done)).toBeVisible();
    if (await done.isVisible()) break;
    if (await next.isVisible()) {
      await next.click();
      continue;
    }
    const text = (await shell.innerText()).replace(/\s+/g, " ");
    prompts.push(text);
    const step = steps.find((s) => s.prompt.test(text));
    if (!step) throw new Error(`no scripted answer for exercise: ${text.slice(0, 120)}`);
    const goWrong = wrongLeft > 0 && step === steps[0];
    if (goWrong) { wrongLeft--; wrongAnswers++; } else rightAnswers++;
    const answer = goWrong ? step.wrong : step.right;
    if (step.kind === "choice") {
      await shell.getByRole("radio", { name: answer, exact: true }).click();
    } else if (step.kind === "order") {
      // Word-order tiles are shuffled; click them by text in the answer order.
      for (const word of answer.split(" ")) {
        await shell.locator(".word-bank").getByRole("button", { name: word, exact: true }).click();
      }
    } else {
      await shell.getByRole("textbox").fill(answer);
    }
    await shell.getByRole("button", { name: "Check", exact: true }).click();
    const banner = page.locator(".feedback-banner").first();
    await expect(banner).toHaveClass(goWrong ? /incorrect/ : /correct/);
    await page.getByRole("button", { name: "Continue", exact: true }).click();
  }
  await page.waitForURL(/\/lessons\/[^/]+\/done$/);
  return { wrongAnswers, rightAnswers, prompts };
}

/**
 * Review items come due 10 minutes after a miss; there is no time travel in the API, so the test
 * pulls them (and the lexeme SRS rows) into the past directly in the throwaway e2e database.
 */
export async function makeReviewsDue(email: string): Promise<number> {
  const { default: pg } = await import("pg");
  const client = new pg.Client({
    connectionString: process.env.E2E_DATABASE_URL ?? "postgresql://ls:e2e-local@db:5432/ls",
  });
  await client.connect();
  try {
    const r = await client.query(
      "UPDATE review_items SET due_at = now() - interval '1 hour' WHERE user_id = (SELECT id FROM users WHERE email = $1)",
      [email],
    );
    await client.query(
      "UPDATE user_lexeme_srs SET due_at = now() - interval '1 hour' WHERE user_id = (SELECT id FROM users WHERE email = $1)",
      [email],
    );
    return r.rowCount ?? 0;
  } finally {
    await client.end();
  }
}
