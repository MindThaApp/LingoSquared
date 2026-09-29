import type { QueryClient } from '@tanstack/react-query'

// Everything an answered review/practice/checkpoint item can change. The
// ["units"] key is a prefix, so it also hits ["units", courseId].
export function invalidateProgressQueries(queryClient: QueryClient) {
  for (const key of ['progress', 'xp', 'streak', 'quests', 'reviews-due', 'units']) {
    void queryClient.invalidateQueries({ queryKey: [key] })
  }
}
