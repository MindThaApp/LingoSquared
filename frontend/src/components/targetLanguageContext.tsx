import { createContext, useContext } from "react";

// The language the learner is currently practising (the exercise's answer
// language). Null/undefined = unknown; TextBlock then falls back to hiding the
// speaker for blocks in the UI language.
export const TargetLanguageContext = createContext<string | null>(null);

export function useTargetLanguage(): string | null {
  return useContext(TargetLanguageContext);
}
