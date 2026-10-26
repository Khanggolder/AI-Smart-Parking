
import PolygonEditor from "./pages/PolygonEditor";
import { useSearchParams } from "react-router-dom";

import ParkingLots from "./pages/ParkingLots";
import Cameras from "./pages/Cameras";

import { useEffect, useState } from "react";
import {
  BrowserRouter,
  Navigate,
  Outlet,
  Route,
  Routes,
  useLocation,
} from "react-router-dom";

import MainLayout from "./layouts/MainLayout";
import Dashboard from "./pages/Dashboard";
import Login from "./pages/Login";

import {
  TOKEN_KEY,
  getCurrentUser,
  loginWithPassword,
} from "./api/auth";

import "./App.css";

function ComingSoon({ title }) {
  return (
    <section className="content-card">
      <h2>{title}</h2>
      <p>Chức năng đang được phát triển.</p>
    </section>
  );
}

function LoadingSession() {
  return (
    <main className="session-loading">
      Đang kiểm tra phiên đăng nhập...
    </main>
  );
}

function ProtectedRoute({ auth }) {
  const location = useLocation();

  if (auth.status === "checking") {
    return <LoadingSession />;
  }

  if (auth.status !== "authenticated") {
    return (
      <Navigate
        to="/login"
        state={{ from: location.pathname }}
        replace
      />
    );
  }

  return <Outlet />;
}

function AdminRoute({ auth }) {
  if (auth.role !== "admin") {
    return (
      <section className="content-card">
        <h2>Không có quyền truy cập</h2>
        <p>Chỉ Admin được chỉnh sửa cấu hình ô đỗ.</p>
      </section>
    );
  }

  return <Outlet />;
}

function App() {
  const [auth, setAuth] = useState(() => ({
    status: sessionStorage.getItem(TOKEN_KEY)
      ? "checking"
      : "unauthenticated",
    user: null,
    role: null,
  }));

  useEffect(() => {
    const token = sessionStorage.getItem(TOKEN_KEY);

    if (!token) return;

    let active = true;

    getCurrentUser(token)
      .then((user) => {
        if (!active) return;

        setAuth({
          status: "authenticated",
          user,
          role: user.role,
        });
      })
      .catch(() => {
        if (!active) return;

        sessionStorage.removeItem(TOKEN_KEY);
        setAuth({
          status: "unauthenticated",
          user: null,
          role: null,
        });
      });

    return () => {
      active = false;
    };
  }, []);

  async function handleLogin(username, password) {
    const { token, user } = await loginWithPassword(
      username,
      password
    );

    sessionStorage.setItem(TOKEN_KEY, token);

    setAuth({
      status: "authenticated",
      user,
      role: user.role,
    });
  }

  function handleLogout() {
    sessionStorage.removeItem(TOKEN_KEY);

    setAuth({
      status: "unauthenticated",
      user: null,
      role: null,
    });
  }

  return (
    <BrowserRouter>
      <Routes>
        <Route
          path="/login"
          element={
            auth.status === "checking" ? (
              <LoadingSession />
            ) : auth.status === "authenticated" ? (
              <Navigate to="/" replace />
            ) : (
              <Login onLogin={handleLogin} />
            )
          }
        />

        <Route element={<ProtectedRoute auth={auth} />}>
          <Route
            element={
              <MainLayout
                auth={auth}
                onLogout={handleLogout}
              />
            }
          >
            <Route index element={<Dashboard />} />


            <Route
              path="/parking-lots"
              element={<ParkingLots role={auth.role} />}
            />

            <Route
              path="/cameras"
              element={<Cameras role={auth.role} />}
            />

            <Route element={<AdminRoute auth={auth} />}>
              <Route
                path="/polygon-editor"
                element={<ComingSoon title="Vẽ ô đỗ" />}
              />
            </Route>

            <Route
              path="/history"
              element={<ComingSoon title="Lịch sử" />}
            />

            <Route
              path="/reports"
              element={<ComingSoon title="Báo cáo" />}
            />
          </Route>
        </Route>
        
        
        {import.meta.env.DEV && (
          <>
            <Route
              path="/dev/parking-lots"
              element={<DevPreview page="parking-lots" />}
            />

            <Route
              path="/dev/cameras"
              element={<DevPreview page="cameras" />}
            />
            <Route
              path="/dev/polygon-editor"
              element={<PolygonEditor role="admin" />}
            />
          </>
        )}

        <Route
          path="*"
          element={<Navigate to="/" replace />}
        />
      </Routes>
    </BrowserRouter>
  );
}


function DevPreview({ page }) {
  const [params] = useSearchParams();

  const role =
    params.get("role") === "operator"
      ? "operator"
      : "admin";

  const requestedState = params.get("state");

  const demoState = [
    "ready",
    "loading",
    "error",
    "empty",
  ].includes(requestedState)
    ? requestedState
    : "ready";

  return (
    <main className="main-content">
      <h1>UI Preview – {role.toUpperCase()}</h1>

      <p className="manager-demo">
        Chế độ DEV – Dữ liệu mẫu, không sử dụng Backend.
      </p>

      {page === "parking-lots" ? (
        <ParkingLots
          demo
          role={role}
          demoState={demoState}
        />
      ) : (
        <Cameras
          demo
          role={role}
          demoState={demoState}
        />
      )}
    </main>
  );
}



export default App;
