import type { ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { CatalogApi } from "@lingo/shared/api/endpoints";
import { TargetLanguageContext } from "./targetLanguageContext";

// Provides the COURSE's target language (what the learner is studying) to the
// text blocks below. Resolved from the all-courses list (shared cache key with
// the course picker). With no courseId or no match it provides null, and
// ExerciseRenderer falls back to the exercise's answer_language_code.
export function CourseTargetLanguage({
  courseId,
  children,
}: {
  courseId: string | null | undefined;
  children: ReactNode;
}) {
  const coursesQuery = useQuery({
    queryKey: ["courses", "all"],
    queryFn: () => CatalogApi.allCourses(),
    staleTime: 5 * 60 * 1000,
    enabled: Boolean(courseId),
  });
  const target = courseId
    ? (coursesQuery.data?.find((c) => c.id === courseId)?.target_language ?? null)
    : null;
  return <TargetLanguageContext.Provider value={target}>{children}</TargetLanguageContext.Provider>;
}
