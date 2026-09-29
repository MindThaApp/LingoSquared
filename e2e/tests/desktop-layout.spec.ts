import { test, expect, type Page } from "@playwright/test";
import { COURSE, enBlock, mockedApp, openLessonViaCourseMap, unit, type LessonFixture } from "./mocks";

// Responsive shell: >= 1024px gets the left side rail + right "Your
// progress" sidebar; phones keep the bottom tab bar. At every width the
// page must not scroll horizontally. Fully route-mocked -- see tests/mocks.ts.

const lesson: LessonFixture = {
  id: "lesson-layout",
  unit_id: "unit-1",
  title: "Greetings",
  teaching: [],
  exercises: [
    {
      id: "ex-layout",
      type: "translation",
      order: 1,
      prompt: {
        text_blocks: [enBlock("Good morning, how are you doing today?")],
        answer_language_code: "nl",
        word_bank: ["Goedemorgen", "hoe", "gaat", "het", "vandaag", "met", "jou", "avond", "slecht"],
      },
    },
  ],
};

const units = [
  unit({ id: "unit-1", title: "Basics 1", order: 1, track: "core" as const }),
  unit({ id: "unit-2", title: "Basics 2", order: 2, track: "core" as const, locked: true }),
];

async function expectNoHorizontalScroll(page: Page) {
  const { scrollWidth, clientWidth } = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
  }));
  expect(scrollWidth, `scrollWidth ${scrollWidth} > clientWidth ${clientWidth}`).toBeLessThanOrEqual(clientWidth);
}

test.describe("desktop 1280x800", () => {
  test.use({ viewport: { width: 1280, height: 800 } });

  test("home and course map show the side rail + sidebar without horizontal scroll", async ({ page, baseURL }) => {
    await mockedApp(page, baseURL, { units, lessons: [lesson] });
    const rail = page.getByRole("navigation", { name: "Main navigation" });
    const sidebar = page.getByRole("complementary", { name: "Your progress" });

    await page.goto("/");
    await expect(rail).toBeVisible();
    await expect(rail.getByRole("link", { name: /Home/ })).toHaveAttribute("aria-current", "page");
    await expect(sidebar).toBeVisible();
    await expect(page.locator(".tabbar")).toBeHidden();
    await expectNoHorizontalScroll(page);

    await page.goto(`/courses/${COURSE.id}`);
    await expect(page.getByRole("heading", { name: COURSE.title })).toBeVisible();
    await expect(page.getByRole("button", { name: "Basics 1", exact: true })).toBeVisible();
    await expect(rail).toBeVisible();
    await expect(rail.getByRole("link", { name: /Learn/ })).toHaveClass(/active/);
    await expect(sidebar).toBeVisible();
    // Rail, main column and sidebar sit side by side, not stacked/overlapping.
    const [railBox, mainBox, sideBox] = await Promise.all([
      rail.boundingBox(),
      page.locator(".page-main-col").boundingBox(),
      sidebar.boundingBox(),
    ]);
    expect(railBox && mainBox && sideBox).toBeTruthy();
    expect(railBox!.x + railBox!.width).toBeLessThanOrEqual(mainBox!.x);
    expect(mainBox!.x + mainBox!.width).toBeLessThanOrEqual(sideBox!.x);
    expect(sideBox!.x + sideBox!.width).toBeLessThanOrEqual(1280);
    await expectNoHorizontalScroll(page);
  });

  test("lesson screen has no horizontal scroll (runner hides the rail)", async ({ page, baseURL }) => {
    await mockedApp(page, baseURL, { units, lessons: [lesson] });
    await openLessonViaCourseMap(page, "Basics 1", "Greetings");
    await expect(page.getByTestId("word-bank-tiles")).toBeVisible();
    await expect(page.getByRole("navigation", { name: "Main navigation" })).toHaveCount(0);
    await expectNoHorizontalScroll(page);
  });
});

test.describe("phone 390x844", () => {
  test.use({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });

  test("home and course map have no horizontal scroll and no desktop chrome", async ({ page, baseURL }) => {
    await mockedApp(page, baseURL, { units, lessons: [lesson] });

    await page.goto("/");
    await expect(page.locator(".tabbar")).toBeVisible();
    await expect(page.locator(".side-rail")).toBeHidden();
    await expect(page.locator(".desktop-sidebar")).toBeHidden();
    await expectNoHorizontalScroll(page);

    await page.goto(`/courses/${COURSE.id}`);
    await expect(page.getByRole("button", { name: "Basics 1", exact: true })).toBeVisible();
    await expect(page.locator(".tabbar")).toBeVisible();
    await expect(page.locator(".side-rail")).toBeHidden();
    await expect(page.locator(".desktop-sidebar")).toBeHidden();
    await expectNoHorizontalScroll(page);
  });

  test("lesson screen has no horizontal scroll", async ({ page, baseURL }) => {
    await mockedApp(page, baseURL, { units, lessons: [lesson] });
    await openLessonViaCourseMap(page, "Basics 1", "Greetings");
    await expect(page.getByTestId("word-bank-tiles")).toBeVisible();
    await expectNoHorizontalScroll(page);
  });
});
