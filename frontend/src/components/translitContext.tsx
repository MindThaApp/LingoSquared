import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { CatalogApi } from "@lingo/shared/api/endpoints";
import { useOptionalAuth } from "../auth/AuthContext";
import {
  resolveShowTranslit,
  setTranslitPreference,
  translitAvailableFor,
} from "../lib/translitPreference";

export interface TranslitState {
  /** Romanization lines are displayed (preference resolved, language supported). */
  show: boolean;
  /** The current course's target language has a pronunciation store (toggle is meaningful). */
  available: boolean;
  setShow: (show: boolean) => void;
}

// Default: nothing shown, no toggle (pages without a provider, practice, tests).
const TranslitContext = createContext<TranslitState>({ show: false, available: false, setShow: () => {} });

export function useTranslit(): TranslitState {
  return useContext(TranslitContext);
}

/**
 * Resolves the learner's "Show pronunciation" setting for a course: stored per-user choice,
 * else ON at A1 / OFF from A2. Shares the ["courses","all"] cache with CourseTargetLanguage.
 */
export function TranslitProvider({
  courseId,
  children,
}: {
  courseId: string | null | undefined;
  children: ReactNode;
}) {
  const userId = useOptionalAuth()?.user?.id ?? null;
  const q = useQuery({
    queryKey: ["courses", "all"],
    queryFn: () => CatalogApi.allCourses(),
    staleTime: 5 * 60 * 1000,
    enabled: Boolean(courseId),
  });
  const course = courseId ? q.data?.find((c) => c.id === courseId) : undefined;
  const available = translitAvailableFor(course?.target_language);
  const [override, setOverride] = useState<boolean | null>(null);
  const resolved = override ?? resolveShowTranslit(userId, course?.level ?? null);
  const setShow = useCallback(
    (show: boolean) => {
      setOverride(show);
      setTranslitPreference(userId, show);
    },
    [userId],
  );
  const value = useMemo(
    () => ({ show: available && resolved, available, setShow }),
    [available, resolved, setShow],
  );
  return <TranslitContext.Provider value={value}>{children}</TranslitContext.Provider>;
}

/** For tests and non-course surfaces that want a fixed state. */
export const TranslitStateProvider = TranslitContext.Provider;
