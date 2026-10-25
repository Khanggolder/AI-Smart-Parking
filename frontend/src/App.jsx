
import { useState } from "react";
import {
  BrowserRouter,
  Routes,
  Route,
  Navigate,
} from "react-router-dom";

import MainLayout from "./layouts/MainLayout";
import Dashboard from "./pages/Dashboard";

import "./App.css";

function ComingSoon({ title }) {
  return (
    <section className="content-card">
      <h2>{title}</h2>
      <p>Chức năng đang được phát triển.</p>
    </section>
  );
}

function App() {
  // Khung auth W2: chưa có đăng nhập thật.
  const [auth] = useState({
    status: "unauthenticated",
    user: null,
    role: null,
  });

  return (
    <BrowserRouter>
      <Routes>
        <Route element={<MainLayout auth={auth} />}>
          <Route index element={<Dashboard />} />

          <Route
            path="/parking-lots"
            element={<ComingSoon title="Quản lý bãi xe" />}
          />

          <Route
            path="/cameras"
            element={<ComingSoon title="Camera" />}
          />

          <Route
            path="/polygon-editor"
            element={<ComingSoon title="Vẽ ô đỗ" />}
          />

          <Route
            path="/history"
            element={<ComingSoon title="Lịch sử" />}
          />

          <Route
            path="/reports"
            element={<ComingSoon title="Báo cáo" />}
          />
        </Route>

        <Route
          path="/login"
          element={<ComingSoon title="Đăng nhập" />}
        />

        <Route
          path="*"
          element={<Navigate to="/" replace />}
        />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
