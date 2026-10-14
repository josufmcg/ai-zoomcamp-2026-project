/**
 * Route table for the EFINGES SPA (backlog task 14).
 *
 * The component is intentionally router-agnostic: `main.tsx` wraps it in a
 * `BrowserRouter` and an `AuthProvider`, and tests wrap it in a `MemoryRouter`
 * with a seeded session. That keeps every route assertion cheap and free of a
 * real browser history.
 *
 * Route guarding is declarative: `RequireAuth` sends signed-out visitors to
 * `/login` and a signed-in user with the wrong role to `/forbidden`. The
 * backend re-checks every role on every request, so the guard only decides
 * which screens the UI offers.
 */

import { Navigate, Route, Routes, useLocation } from "react-router-dom";

import { useAuth } from "./auth/AuthContext";
import { homePathForRole, postLoginPath } from "./auth/navigation";
import { RequireAuth } from "./auth/RequireAuth";
import AppShell from "./pages/AppShell";
import {
  AdminHomePage,
  ForbiddenPage,
  ManagerHomePage,
  NotFoundPage,
  OverviewPage,
} from "./pages/HomePages";
import LoginPage from "./pages/LoginPage";
import ResidentHomePage from "./pages/ResidentHomePage";

/** Send a signed-in visitor from `/` to their home screen, others to `/login`. */
function RedirectToHomeOrLogin() {
  const { user } = useAuth();
  return user ? (
    <Navigate to={homePathForRole(user.role)} replace />
  ) : (
    <Navigate to="/login" replace />
  );
}

/**
 * Keep an already signed-in visitor away from the login form.
 *
 * This is where a successful login actually ends up: the login page only hands
 * the credentials to the provider, and the redirect here picks the destination
 * from the path the guard recorded. Doing the redirect in one place avoids two
 * competing navigations when the provider's state update lands.
 */
function LoginRoute() {
  const { user } = useAuth();
  const location = useLocation();
  if (user) {
    return <Navigate to={postLoginPath(location.state, user.role)} replace />;
  }
  return <LoginPage />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<RedirectToHomeOrLogin />} />
      <Route path="/login" element={<LoginRoute />} />

      {/* Signed-in chrome: header, role-filtered sidebar, and content. */}
      <Route
        element={
          <RequireAuth>
            <AppShell />
          </RequireAuth>
        }
      >
        <Route path="/overview" element={<OverviewPage />} />
        <Route
          path="/resident"
          element={
            <RequireAuth roles={["resident"]}>
              <ResidentHomePage />
            </RequireAuth>
          }
        />
        <Route
          path="/manager"
          element={
            <RequireAuth roles={["manager"]}>
              <ManagerHomePage />
            </RequireAuth>
          }
        />
        <Route
          path="/admin"
          element={
            <RequireAuth roles={["administrator"]}>
              <AdminHomePage />
            </RequireAuth>
          }
        />
        <Route path="/forbidden" element={<ForbiddenPage />} />
      </Route>

      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
