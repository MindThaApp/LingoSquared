// Guided first-start state, per user, per device (same localStorage precedent
// as activeCourse.ts). Every access is try/catch'd: storage can throw and
// onboarding state must never break navigation.
export type OnboardingStage = "course" | "goal" | "start";
export type OnboardingStatus = "active" | "done" | "skipped";

export interface OnboardingState {
  status: OnboardingStatus;
  stage: OnboardingStage;
  courseId?: string;
}

const PREFIX = "lingo.onboarding.";
const DEFAULT_STATE: OnboardingState = { status: "active", stage: "course" };

export function getOnboarding(userId: string | null | undefined): OnboardingState {
  if (!userId) return DEFAULT_STATE;
  try {
    const raw = localStorage.getItem(PREFIX + userId);
    if (!raw) return DEFAULT_STATE;
    const p = JSON.parse(raw) as Partial<OnboardingState>;
    const status = p.status === "done" || p.status === "skipped" ? p.status : "active";
    const stage = p.stage === "goal" || p.stage === "start" ? p.stage : "course";
    // A later stage is meaningless without a chosen course: restart at step 1.
    if (status === "active" && stage !== "course" && typeof p.courseId !== "string") return DEFAULT_STATE;
    return { status, stage, courseId: typeof p.courseId === "string" ? p.courseId : undefined };
  } catch {
    return DEFAULT_STATE;
  }
}

export function setOnboarding(userId: string | null | undefined, state: OnboardingState): void {
  if (!userId) return;
  try {
    localStorage.setItem(PREFIX + userId, JSON.stringify(state));
  } catch {
    // ignore
  }
}

/**
 * Whether Home should send this user to the guided first start: a brand-new
 * account (caller passes isBrandNewUser), no course opened yet on this device,
 * and onboarding neither finished nor skipped.
 */
export function shouldShowOnboarding(
  userId: string | null | undefined,
  brandNew: boolean,
  activeCourseId: string | null,
): boolean {
  if (!userId || !brandNew || activeCourseId) return false;
  return getOnboarding(userId).status === "active";
}
