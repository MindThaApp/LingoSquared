import { useQuery } from "@tanstack/react-query";
import { CatalogApi } from "@lingo/shared/api/endpoints";
import type { CefrLevel } from "@lingo/shared/api/types";

// Course CEFR level, from the same ["courses","all"] cache the course picker
// and CourseTargetLanguage use. null while loading / unknown -> typing default.
export function useCourseLevel(courseId: string | null | undefined): CefrLevel | null {
  const q = useQuery({
    queryKey: ["courses", "all"],
    queryFn: () => CatalogApi.allCourses(),
    staleTime: 5 * 60 * 1000,
    enabled: Boolean(courseId),
  });
  if (!courseId) return null;
  return q.data?.find((c) => c.id === courseId)?.level ?? null;
}
