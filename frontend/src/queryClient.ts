import { QueryClient } from '@tanstack/react-query'

// Default staleTime: 0 (react-query's own default) meant every screen
// focus/app-switch refetched every mounted query -- expensive network
// chatter on mobile for data that changes at most once per lesson/review/
// practice completion. 30s keeps genuinely time-sensitive reads (due
// counts, quests) reasonably fresh while killing the worst of the
// refetch-on-focus storm; queries that need to be fresher or staler
// override this per-query, same as CoursePickerPage already does.
//
// Lives in its own module (not main.tsx, which renders on import) so
// AuthContext can clear it on logout/401 and tests can import it.
// Query keys are NOT user-scoped, so the cache MUST be cleared whenever
// the session ends or a second user on the device sees the first's data.
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
    },
  },
})
