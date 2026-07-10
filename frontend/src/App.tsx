import { Suspense, lazy } from "react";
import { Route, Routes } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { NavBar } from "./components/layout/NavBar";
import { ProtectedRoute } from "./components/layout/ProtectedRoute";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { FeedbackWidget } from "./components/FeedbackWidget";
import { HomePage } from "./pages/HomePage";
import { LoginPage } from "./pages/LoginPage";
import { RegisterPage } from "./pages/RegisterPage";
import { CoursePickerPage } from "./pages/CoursePickerPage";
import { LevelCheckPage } from "./pages/LevelCheckPage";
import { CourseUnitsPage } from "./pages/CourseUnitsPage";
import { UnitLessonsPage } from "./pages/UnitLessonsPage";
import { CheckpointPage } from "./pages/CheckpointPage";
import { PracticeFeedPage } from "./pages/PracticeFeedPage";
import { LessonRunnerPage } from "./pages/LessonRunnerPage";
import { LessonCompletePage } from "./pages/LessonCompletePage";
import { ReviewPage } from "./pages/ReviewPage";
import { VocabularyPage } from "./pages/VocabularyPage";
import { ProfilePage } from "./pages/ProfilePage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { PrivacyPolicyPage } from "./pages/PrivacyPolicyPage";
import { TermsOfServicePage } from "./pages/TermsOfServicePage";

// Route-level code splitting: AdminContentPage is genuinely admin-only, so it
// stays out of the initial bundle everyone downloads. Core daily-use pages
// (Home, lesson flow, practice, review) stay statically imported — lazy-loading
// those would add a network round-trip to the common path for no win.
// CheckpointPage/LevelCheckPage were measured (2026-07-10) and deliberately NOT
// lazy-loaded: CheckpointPage shares exercise-runner code with the static
// LessonRunnerPage, so splitting it forces rolldown to hoist the shared modules
// into separate eagerly-modulepreloaded chunks — the extra gzip-stream overhead
// (~+3 kB on the eager payload) outweighed the ~7 kB (minified, ~2.8 kB gzip)
// of page code it deferred. Re-measure the total eager payload (entry +
// modulepreload links in dist/index.html, not just the index-*.js line) before
// lazy-loading any other page here.
const AdminContentPage = lazy(() =>
  import("./pages/AdminContentPage").then((m) => ({ default: m.AdminContentPage })),
);

function App() {
  const { t } = useTranslation();
  return (
    <div className="app">
      <NavBar />
      <main className="app-main">
        <ErrorBoundary>
          <Suspense
            fallback={<div className="page-loading">{t("common.loading")}</div>}
          >
            <Routes>
              <Route path="/login" element={<LoginPage />} />
              <Route path="/register" element={<RegisterPage />} />
              {/* Public legal pages — must stay reachable logged-out (a
                  prospective user reads these before registering). */}
              <Route path="/privacy" element={<PrivacyPolicyPage />} />
              <Route path="/terms" element={<TermsOfServicePage />} />
              <Route
                path="/courses"
                element={
                  <ProtectedRoute>
                    <CoursePickerPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/courses/:courseId/level"
                element={
                  <ProtectedRoute>
                    <LevelCheckPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/courses/:courseId"
                element={
                  <ProtectedRoute>
                    <CourseUnitsPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/units/:unitId"
                element={
                  <ProtectedRoute>
                    <UnitLessonsPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/units/:unitId/checkpoint"
                element={
                  <ProtectedRoute>
                    <CheckpointPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/lessons/:lessonId"
                element={
                  <ProtectedRoute>
                    <LessonRunnerPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/lessons/:lessonId/done"
                element={
                  <ProtectedRoute>
                    <LessonCompletePage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/practice"
                element={
                  <ProtectedRoute>
                    <PracticeFeedPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/review"
                element={
                  <ProtectedRoute>
                    <ReviewPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/vocabulary"
                element={
                  <ProtectedRoute>
                    <VocabularyPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/profile"
                element={
                  <ProtectedRoute>
                    <ProfilePage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/admin/content"
                element={
                  <ProtectedRoute>
                    <AdminContentPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/"
                element={
                  <ProtectedRoute>
                    <HomePage />
                  </ProtectedRoute>
                }
              />
              <Route path="*" element={<NotFoundPage />} />
            </Routes>
          </Suspense>
        </ErrorBoundary>
      </main>
      <FeedbackWidget />
    </div>
  );
}

export default App;
