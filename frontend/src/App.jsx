import { Navigate, Route, Routes } from "react-router-dom";

import { useAuth } from "./components/AuthProvider";
import ProtectedRoute from "./components/ProtectedRoute";
import DashboardPage from "./pages/DashboardPage";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";

function HomeRedirect() {
  const auth = useAuth();
  return <Navigate to={auth.isAuthenticated ? "/dashboard" : "/login"} replace />;
}

export default function App() {
  return (
    <main className="app-shell">
      <Routes>
        <Route path="/" element={<HomeRedirect />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <DashboardPage />
            </ProtectedRoute>
          }
        />
      </Routes>
    </main>
  );
}
