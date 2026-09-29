// The course the learner most recently opened, per user, per device (same
// localStorage precedent as lastUnitPreferences.ts). Lets the Learn tab and
// Home "Learn" button resume the current course instead of always showing
// the course picker. Every access is try/catch'd: storage can throw (private
// mode, quota, disabled) and a preference must never break navigation.
const PREFIX = "lingo.activeCourse.";

export function getActiveCourse(userId: string | null | undefined): string | null {
  if (!userId) return null;
  try {
    return localStorage.getItem(PREFIX + userId) || null;
  } catch {
    return null;
  }
}

export function setActiveCourse(userId: string | null | undefined, courseId: string): void {
  if (!userId || !courseId) return;
  try {
    localStorage.setItem(PREFIX + userId, courseId);
  } catch {
    // ignore
  }
}

export function clearActiveCourse(userId: string | null | undefined): void {
  if (!userId) return;
  try {
    localStorage.removeItem(PREFIX + userId);
  } catch {
    // ignore
  }
}

// Route the Learn entry points send the learner to.
export function learnPath(userId: string | null | undefined): string {
  const courseId = getActiveCourse(userId);
  return courseId ? `/courses/${courseId}` : "/courses";
}
