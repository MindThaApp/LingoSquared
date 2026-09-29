import { Suspense, lazy } from "react";
import { Route, Routes, matchPath, useLocation } from "react-router-dom";
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
import { LessonRunnerPage } from "./pages/LessonRunnerPage";
import { LessonCompletePage } from "./pages/LessonCompletePage";
import { ReviewPage } from "./pages/ReviewPage";
import { NotFoundPage } from "./pages/NotFoundPage";

// Route-level code splitting: rarely-visited / non-core pages are lazy so the
// entry bundle stays small. Core daily-use pages (Login, Register, Home,
// CoursePicker, LessonRunner, review, level/units) stay static — lazy-loading
// those would add a round-trip to the common path.
// The 2026-07-10 measurement had lazy CheckpointPage INCREASE the eager payload
// (shared exercise-runner code hoisted into modulepreloaded chunks). Re-measured
// 2026-09-29 on the TOTAL eager payload (entry + every modulepreload/script in
// dist/index.html, per-file gzip summed): CheckpointPage and PracticeFeedPage
// both eager 155,122 B; only CheckpointPage lazy 154,746 B; only PracticeFeedPage
// lazy 153,987 B; both lazy 153,345 B. Each lazy page lowered the payload, so
// both are lazy now.
// Re-measure the same way before changing any of this.
const PrivacyPolicyPage = lazy(() =>
  import("./pages/PrivacyPolicyPage").then((m) => ({ default: m.PrivacyPolicyPage })),
);
const TermsOfServicePage = lazy(() =>
  import("./pages/TermsOfServicePage").then((m) => ({ default: m.TermsOfServicePage })),
);
const VocabularyPage = lazy(() =>
  import("./pages/VocabularyPage").then((m) => ({ default: m.VocabularyPage })),
);
const PlacementTestPage = lazy(() =>
  import("./pages/PlacementTestPage").then((m) => ({ default: m.PlacementTestPage })),
);
const ProfilePage = lazy(() =>
  import("./pages/ProfilePage").then((m) => ({ default: m.ProfilePage })),
);
const CheckpointPage = lazy(() =>
  import("./pages/CheckpointPage").then((m) => ({ default: m.CheckpointPage })),
);
const PracticeFeedPage = lazy(() =>
  import("./pages/PracticeFeedPage").then((m) => ({ default: m.PracticeFeedPage })),
);
const ShowcasePage = lazy(() => import("./pages/ShowcasePage"));
const AdminContentPage = lazy(() =>
  import("./pages/AdminContentPage").then((m) => ({ default: m.AdminContentPage })),
);

// Full-screen runner routes: no tab bar / feedback widget while mid-exercise.
const RUNNER_PATTERNS = ["/lessons/:lessonId", "/review", "/units/:unitId/checkpoint"];

function App() {
  const { t } = useTranslation();
  const location = useLocation();
  const isRunner = RUNNER_PATTERNS.some((path) => matchPath({ path, end: true }, location.pathname));
  return (
    <div className="app">
      {!isRunner && <NavBar />}
      <main className="app-main">
        <ErrorBoundary key={location.pathname}>
          <Suspense
            fallback={
              <div className="page-loading" role="status" aria-live="polite">
                {t("common.loading")}
              </div>
            }
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
                path="/courses/:courseId/placement"
                element={
                  <ProtectedRoute>
                    <PlacementTestPage />
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
                path="/showcase"
                element={
                  <ProtectedRoute>
                    <ShowcasePage />
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
      {!isRunner && <FeedbackWidget />}
    </div>
  );
}

export default App;
