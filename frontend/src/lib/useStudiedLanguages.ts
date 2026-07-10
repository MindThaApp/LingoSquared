import { useMemo } from "react";
import { useQueries, useQuery } from "@tanstack/react-query";
import { CatalogApi, ProgressApi } from "@lingo/shared/api/endpoints";

// The set of language codes actually relevant to this learner right now —
// both directions of every course they have real progress in (skill_progress
// from /me/progress, the same "has this learner actually done anything
// here" signal HomePage/ProfilePage already use elsewhere), not every one
// of the 10 languages the app knows about. A per-language settings control
// (TTS speed, previously voice choice) is more usable when it isn't a list
// of mostly-irrelevant languages with zero content for this account.
export function useStudiedLanguages(): { languageCodes: string[]; isLoading: boolean } {
  const progressQuery = useQuery({ queryKey: ["progress"], queryFn: ProgressApi.progress });
  const courseIds = useMemo(
    () => [...new Set((progressQuery.data?.skill_progress ?? []).map((s) => s.course_id))],
    [progressQuery.data],
  );

  const courseQueries = useQueries({
    queries: courseIds.map((courseId) => ({
      queryKey: ["course", courseId],
      queryFn: () => CatalogApi.course(courseId),
      enabled: !!courseId,
    })),
  });

  const languageCodes = useMemo(() => {
    const codes = new Set<string>();
    for (const query of courseQueries) {
      if (query.data) {
        codes.add(query.data.source_language);
        codes.add(query.data.target_language);
      }
    }
    return [...codes].sort();
  }, [courseQueries]);

  const isLoading = progressQuery.isLoading || courseQueries.some((q) => q.isLoading);
  return { languageCodes, isLoading };
}
