import { test, expect } from "@playwright/test";
import { ACTIVE_COURSE_KEY, COURSE, enBlock, mockedApp, unit, type LessonFixture } from "./mocks";

// Course map "Situations" shelf (UnitSummary.track === "situation"):
// optional units live in a collapsed shelf below the core path, are always
// open (never locked), and never become the recommended/continue unit.
// Fully route-mocked -- see tests/mocks.ts.

// 1280px so the desktop sidebar (with its "Next lesson" Continue card, the
// app's continue affordance) is on screen alongside the path.
test.use({ viewport: { width: 1280, height: 800 } });

function lessonFor(unitId: string, id: string, title: string): LessonFixture {
  return {
    id,
    unit_id: unitId,
    title,
    teaching: [],
    exercises: [{ id: `${id}-ex`, type: "translation", order: 1, prompt: { text_blocks: [enBlock("Hello")] } }],
  };
}

test("situation unit sits in a collapsed shelf, is unlocked, and is never the recommended/continue unit", async ({ page, baseURL }) => {
  await mockedApp(page, baseURL, {
    // The situation unit is deliberately FIRST in the payload and marked
    // locked by the server: if the page failed to partition by track it
    // would be the recommended unit, the sidebar's next lesson, and locked.
    units: [
      unit({ id: "sit-1", title: "At the café", order: 1, track: "situation", locked: true, content_key: "nl.a1.sit01.cafe" }),
      unit({ id: "core-1", title: "Basics 1", order: 2, track: "core", content_key: "nl.a1.unit01.basics" }),
      unit({ id: "core-2", title: "Basics 2", order: 3, track: "core", locked: true, content_key: "nl.a1.unit02.basics" }),
    ],
    lessons: [lessonFor("sit-1", "lesson-sit", "Ordering coffee"), lessonFor("core-1", "lesson-core", "Hello there")],
    storage: {
      // Self-reported "beginner" -> CourseUnitsPage recommends the first
      // reading/writing unit; the sidebar resumes this course.
      [`course-level-${COURSE.id}`]: "beginner",
      [ACTIVE_COURSE_KEY]: COURSE.id,
    },
  });

  await page.goto(`/courses/${COURSE.id}`);
  await expect(page.getByRole("button", { name: "Basics 1", exact: true })).toBeVisible();

  // Collapsed by default.
  const toggle = page.getByRole("button", { name: /Situations/ });
  await expect(toggle).toBeVisible();
  await expect(toggle).toHaveAttribute("aria-expanded", "false");
  await expect(page.getByRole("button", { name: /At the café/ })).toHaveCount(0);

  // Recommended badge: exactly one, on the first CORE unit.
  const recommended = page.getByText("Recommended for you");
  await expect(recommended).toHaveCount(1);
  await expect(page.locator(".path-node", { hasText: "Basics 1" })).toContainText("Recommended for you");

  // Continue affordance (desktop sidebar "Next lesson") points at the core unit.
  const next = page.getByTestId("sidebar-next-lesson");
  await expect(next).toContainText("Hello there");
  await expect(next).toContainText("Basics 1");
  await expect(next).not.toContainText("Ordering coffee");
  await expect(
    page.getByRole("complementary", { name: "Your progress" }).getByRole("link", { name: "Continue" }),
  ).toHaveAttribute("href", "/lessons/lesson-core");

  // Expand.
  await toggle.click();
  await expect(toggle).toHaveAttribute("aria-expanded", "true");
  const situation = page.getByRole("button", { name: "At the café", exact: true }); // no " (locked)" suffix
  await expect(situation).toBeVisible();
  await expect(situation).toBeEnabled();
  const node = page.locator(".path-node", { hasText: "At the café" });
  await expect(node).not.toHaveClass(/\blocked\b/);
  await expect(node).not.toContainText("Recommended for you");
  await expect(node).not.toContainText("Finish the earlier units to unlock");
  // Still only the one core recommendation after expanding.
  await expect(recommended).toHaveCount(1);

  // Unlocked for real: it opens the unit.
  await situation.click();
  await page.waitForURL("**/units/sit-1");
  await expect(page.getByRole("link", { name: /Ordering coffee/ })).toBeVisible();
});

test("all-core course renders no Situations shelf", async ({ page, baseURL }) => {
  await mockedApp(page, baseURL, {
    units: [
      unit({ id: "core-1", title: "Basics 1", order: 1, track: "core" }),
      // Older servers omit `track`; missing must be treated as core.
      unit({ id: "core-2", title: "Basics 2", order: 2 }),
    ],
  });

  await page.goto(`/courses/${COURSE.id}`);
  await expect(page.getByRole("button", { name: "Basics 1", exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Basics 2", exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: /Situations/ })).toHaveCount(0);
  await expect(page.getByText("Optional real-life scenarios")).toHaveCount(0);
  await expect(page.locator(".situations-shelf")).toHaveCount(0);
});
