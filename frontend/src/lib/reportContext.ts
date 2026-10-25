import { matchPath } from "react-router-dom";

// Where the learner was when something went wrong. Route-derived ids come
// from the URL; ids that only exist in component state (course in route
// state, the exercise on screen) are registered by the pages that own them.
export interface ReportContext {
  courseId?: string;
  itemId?: string;
}

let registered: ReportContext = {};

export function setReportContext(patch: ReportContext): () => void {
  registered = { ...registered, ...patch };
  return () => {
    for (const key of Object.keys(patch) as Array<keyof ReportContext>) {
      if (registered[key] === patch[key]) delete registered[key];
    }
  };
}

export function resetReportContext(): void {
  registered = {};
}

const PATTERNS: Array<{ path: string; key: "lesson_id" | "unit_id" | "course_id"; param: string }> = [
  { path: "/lessons/:id/*", key: "lesson_id", param: "id" },
  { path: "/units/:id/*", key: "unit_id", param: "id" },
  { path: "/courses/:id/*", key: "course_id", param: "id" },
];

// "/lessons/abc/done" -> "/lessons/:id/done": a stable route for grouping.
export function routeTemplate(pathname: string): string {
  return pathname
    .split("/")
    .map((seg, i, all) => (i > 0 && /^(lessons|units|courses)$/.test(all[i - 1]) ? ":id" : seg))
    .join("/");
}

export function collectReportTags(pathname: string): Record<string, string> {
  const tags: Record<string, string> = { route: routeTemplate(pathname) };
  for (const { path, key, param } of PATTERNS) {
    const m = matchPath({ path, end: false }, pathname);
    const id = m?.params[param];
    if (id) tags[key] = id;
  }
  if (registered.courseId) tags.course_id = registered.courseId;
  if (registered.itemId) tags.item_id = registered.itemId;
  return tags;
}
