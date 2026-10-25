import { afterEach, describe, expect, it } from "vitest";
import { collectReportTags, resetReportContext, routeTemplate, setReportContext } from "./reportContext";

afterEach(resetReportContext);

describe("reportContext", () => {
  it("templates ids out of the route", () => {
    expect(routeTemplate("/lessons/abc/done")).toBe("/lessons/:id/done");
    expect(routeTemplate("/profile")).toBe("/profile");
  });

  it("collects ids from the URL and registered state", () => {
    const off = setReportContext({ courseId: "c1", itemId: "i1" });
    expect(collectReportTags("/lessons/l9")).toEqual({
      route: "/lessons/:id",
      lesson_id: "l9",
      course_id: "c1",
      item_id: "i1",
    });
    off();
    expect(collectReportTags("/lessons/l9")).toEqual({ route: "/lessons/:id", lesson_id: "l9" });
  });
});
