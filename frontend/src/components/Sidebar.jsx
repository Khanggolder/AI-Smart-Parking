
import {
  LayoutDashboard,
  CarFront,
  Camera,
  History,
  ChartColumn,
  ParkingCircle,
} from "lucide-react";

const menuItems = [
  { name: "Dashboard", icon: LayoutDashboard },
  { name: "Quản lý bãi xe", icon: CarFront },
  { name: "Camera", icon: Camera },
  { name: "Vẽ ô đỗ", icon: ParkingCircle },
  { name: "Lịch sử", icon: History },
  { name: "Báo cáo", icon: ChartColumn },
];

function Sidebar({ activePage, onNavigate }) {
  return (
    <aside className="sidebar">
      <h2>AI Smart Parking</h2>

      <nav>
        {menuItems.map((item) => {
          const Icon = item.icon;

          return (
            <button
              type="button"
              key={item.name}
              className={
                activePage === item.name
                  ? "menu-item active"
                  : "menu-item"
              }
              onClick={() => onNavigate(item.name)}
            >
              <Icon size={20} />
              <span>{item.name}</span>
            </button>
          );
        })}
      </nav>
    </aside>
  );
}

export default Sidebar;
