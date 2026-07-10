import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import './index.css'
import './i18n'
import App from './App.tsx'
import { AuthProvider } from './auth/AuthContext'

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
