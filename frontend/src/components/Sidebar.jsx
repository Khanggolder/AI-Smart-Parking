
import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  CarFront,
  Camera,
  History,
  ChartColumn,
  ParkingCircle,
} from "lucide-react";

const menuItems = [
  { name: "Dashboard", path: "/", icon: LayoutDashboard },
  { name: "Quản lý bãi xe", path: "/parking-lots", icon: CarFront },
  { name: "Camera", path: "/cameras", icon: Camera },
  {
    name: "Vẽ ô đỗ",
    path: "/polygon-editor",
    icon: ParkingCircle,
    adminOnly: true,
  },
  { name: "Lịch sử", path: "/history", icon: History },
  { name: "Báo cáo", path: "/reports", icon: ChartColumn },
];

function Sidebar({ role }) {
  const visibleItems = menuItems.filter(
    (item) => !item.adminOnly || role === "admin"
  );

  return (
    <aside className="sidebar">
      <h2>AI Smart Parking</h2>

      <nav>
        {visibleItems.map((item) => {
          const Icon = item.icon;

          return (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === "/"}
              className={({ isActive }) =>
                isActive
                  ? "menu-item active"
                  : "menu-item"
              }
            >
              <Icon size={20} />
              <span>{item.name}</span>
            </NavLink>
          );
        })}
      </nav>
    </aside>
  );
}

export default Sidebar;
