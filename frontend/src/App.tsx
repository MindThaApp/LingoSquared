import { Route, Routes } from "react-router-dom";
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
import { AdminContentPage } from "./pages/AdminContentPage";
import { NotFoundPage } from "./pages/NotFoundPage";

function App() {
  return (
    <div className="app">
      <NavBar />
      <main className="app-main">
        <ErrorBoundary>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
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
        </ErrorBoundary>
      </main>
      <FeedbackWidget />
    </div>
  );
}

export default App;
