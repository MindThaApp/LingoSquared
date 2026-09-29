import axe from "axe-core";
import { expect } from "vitest";

// Runs axe-core against a rendered container and returns only
// serious/critical violations. color-contrast is disabled because jsdom
// cannot compute rendered colors — contrast is checked against the
// index.css tokens instead.
//
// axe-core throws "Axe is already running" if run() overlaps, and a run that
// outlives its test's timeout keeps going in the background. Serialize all
// runs through a module-level chain so a slow run can never collide with (and
// cascade-fail) later tests. The full rule set is kept (minus color-contrast)
// so no rule the tests intend to cover is dropped.
let axeQueue: Promise<unknown> = Promise.resolve();

function runAxeSerialized(container: Element): Promise<axe.AxeResults> {
  const run = axeQueue.catch(() => undefined).then(() =>
    axe.run(container, {
      resultTypes: ["violations"],
      rules: { "color-contrast": { enabled: false } },
      performanceTimer: false,
    }),
  );
  axeQueue = run;
  return run;
}

export async function seriousViolations(container: Element = document.body) {
  const results = await runAxeSerialized(container);
  return results.violations.filter(
    (v) => v.impact === "serious" || v.impact === "critical",
  );
}

export async function expectNoSeriousA11yViolations(container?: Element) {
  const violations = await seriousViolations(container);
  expect(
    violations.map(
      (v) => `${v.id}: ${v.help} -> ${v.nodes.map((n) => n.target.join(" ")).join(", ")}`,
    ),
  ).toEqual([]);
}
