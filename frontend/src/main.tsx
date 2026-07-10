import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { configureApi } from '@lingo/shared/api/client'
import { configureAnswerInputModeStore } from '@lingo/shared/lib/answerInputMode'
import './index.css'
import './i18n'
import App from './App.tsx'
import { AuthProvider } from './auth/AuthContext'
import { installGlobalCrashReporting } from './lib/crashReporter'

// @lingo/shared's api/client.ts and lib/answerInputMode.ts moved out of
// frontend/src (Phase 0 of the mobile plan, see CLAUDE.md) and can no
// longer reach import.meta.env/localStorage themselves -- both MUST be
// configured here, synchronously, before anything below can render and
// possibly fire an API call or read the answer-input-mode preference.
// Module top-level code (this whole file, imports included) always
// finishes running before React commits the first render or fires any
// effect, so placing these calls before createRoot(...).render(...) is
// sufficient; no explicit ordering hack needed.
const ACCESS_TOKEN_STORAGE_KEY = 'access_token'

configureApi({
  baseUrl: import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000',
  // Mirrors the original client.ts's FEEDBACK_BASE_URL fallback chain
  // exactly: VITE_FEEDBACK_API_URL, else the same base URL as everything
  // else. See docs/CONTRACT.md's "General app/page feedback" section and
  // CLAUDE.md's "Feedback/issue-report collection strategy" entry.
  feedbackBaseUrl:
    import.meta.env.VITE_FEEDBACK_API_URL ??
    (import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'),
  tokenStorage: {
    get: () => localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY),
    set: (token) => localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, token),
    clear: () => localStorage.removeItem(ACCESS_TOKEN_STORAGE_KEY),
  },
})

// Automatic crash reporting (window error / unhandledrejection ->
// POST /feedback, category app_bug). Must come after configureApi()
// above -- FeedbackApi throws if the client isn't configured yet.
// ErrorBoundary.componentDidCatch reports through the same path.
installGlobalCrashReporting()

// Same storage key/behavior as the pre-extraction answerInputMode.ts,
// including the private-browsing/quota-error swallow on set.
const ANSWER_INPUT_MODE_STORAGE_KEY = 'answer-input-mode'

configureAnswerInputModeStore({
  get: () => localStorage.getItem(ANSWER_INPUT_MODE_STORAGE_KEY),
  set: (mode) => {
    try {
      localStorage.setItem(ANSWER_INPUT_MODE_STORAGE_KEY, mode)
    } catch {
      // Private-browsing/quota errors: not worth surfacing, just don't persist.
    }
  },
})

// Default staleTime: 0 (react-query's own default) meant every screen
// focus/app-switch refetched every mounted query -- expensive network
// chatter on mobile for data that changes at most once per lesson/review/
// practice completion. 30s keeps genuinely time-sensitive reads (due
// counts, quests) reasonably fresh while killing the worst of the
// refetch-on-focus storm; queries that need to be fresher or staler
// override this per-query, same as CoursePickerPage already does.
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
    },
  },
})

if ('serviceWorker' in navigator && import.meta.env.PROD) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch(() => {})
  })
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          <App />
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
)
