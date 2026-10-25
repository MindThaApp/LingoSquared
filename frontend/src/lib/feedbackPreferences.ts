// Per-device answer-feedback preferences (same localStorage precedent as
// ttsSpeedPreferences.ts). Both default ON; a stored "0" turns them off.
// Every access is try/catch'd: storage can throw and a preference must never
// break the lesson.
const AUTOPLAY_KEY = "feedback-autoplay-answer";
const CUES_KEY = "feedback-cues";

function read(key: string): boolean {
  try {
    return localStorage.getItem(key) !== "0";
  } catch {
    return true;
  }
}

function write(key: string, on: boolean): void {
  try {
    if (on) localStorage.removeItem(key);
    else localStorage.setItem(key, "0");
  } catch {
    // ignore
  }
}

export const getAutoPlayAnswer = () => read(AUTOPLAY_KEY);
export const setAutoPlayAnswer = (on: boolean) => write(AUTOPLAY_KEY, on);
/** Short sound + vibration on correct / wrong answers. */
export const getFeedbackCues = () => read(CUES_KEY);
export const setFeedbackCues = (on: boolean) => write(CUES_KEY, on);
