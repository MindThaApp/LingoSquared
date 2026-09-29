import axe from "axe-core";
import { expect } from "vitest";

// Runs axe-core against a rendered container and returns only
// serious/critical violations. color-contrast is disabled because jsdom
// cannot compute rendered colors — contrast is checked against the
// index.css tokens instead.
export async function seriousViolations(container: Element = document.body) {
  const results = await axe.run(container, {
    resultTypes: ["violations"],
    rules: { "color-contrast": { enabled: false } },
  });
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
