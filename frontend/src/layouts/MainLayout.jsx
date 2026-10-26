
import { Outlet, useLocation } from "react-router-dom";
import Sidebar from "../components/Sidebar";
import Header from "../components/Header";

const pageTitles = {
  "/": "Dashboard",
  "/parking-lots": "Quản lý bãi xe",
  "/cameras": "Camera",
  "/polygon-editor": "Vẽ ô đỗ",
  "/history": "Lịch sử",
  "/reports": "Báo cáo",
};

function MainLayout({ auth, onLogout }) {
  const { pathname } = useLocation();
  const title = pageTitles[pathname] ?? "AI Smart Parking";

  return (
    <div className="app-container">
      <Sidebar role={auth.role} />

      <main className="main-content">
        <Header
          title={title}
          auth={auth}
          onLogout={onLogout}
        />
        <Outlet />
      </main>
    </div>
  );
}

export default MainLayout;
