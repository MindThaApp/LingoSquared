// Exercise types whose audio prompt should autoplay once on mount.
const LISTENING_TYPES = new Set([
  "listen_select",
  "listen_type",
  "listen_order",
  "dictation",
  "dialogue_comprehension",
]);

export function isListeningExercise(type: string): boolean {
  return LISTENING_TYPES.has(type);
}
