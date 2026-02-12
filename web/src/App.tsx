import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { getToken } from "./lib/api";
import LoginPage from "./pages/LoginPage";
import AppPage from "./pages/AppPage";

function RequireAuth({ children }: { children: JSX.Element }) {
  return getToken() ? children : <Navigate to="/login" replace />;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Navigate to="/app" replace />} />
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/app"
          element={
            <RequireAuth>
              <AppPage />
            </RequireAuth>
          }
        />
      </Routes>
    </BrowserRouter>
  );
}
