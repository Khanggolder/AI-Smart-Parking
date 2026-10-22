
import { useState } from "react";
import {
  LayoutDashboard,
  CarFront,
  Camera,
  History,
  ChartColumn,
  ParkingCircle,
} from "lucide-react";

import "./App.css";

const menuItems = [
  { name: "Dashboard", icon: LayoutDashboard },
  { name: "Quản lý bãi xe", icon: CarFront },
  { name: "Camera", icon: Camera },
  { name: "Vẽ ô đỗ", icon: ParkingCircle },
  { name: "Lịch sử", icon: History },
  { name: "Báo cáo", icon: ChartColumn },
];

function App() {
  const [activePage, setActivePage] = useState("Dashboard");

  const stats = [
    { title: "Tổng số ô", value: 100, color: "#2563eb" },
    { title: "Ô trống", value: 35, color: "#16a34a" },
    { title: "Đã có xe", value: 60, color: "#dc2626" },
    { title: "Chưa xác định", value: 5, color: "#ca8a04" },
  ];

  return (
    <div className="app-container">
      <aside className="sidebar">
        <h2>AI Smart Parking</h2>

        <nav>
          {menuItems.map((item) => {
            const Icon = item.icon;

            return (
              <button
                key={item.name}
                className={
                  activePage === item.name
                    ? "menu-item active"
                    : "menu-item"
                }
                onClick={() => setActivePage(item.name)}
              >
                <Icon size={20} />
                <span>{item.name}</span>
              </button>
            );
          })}
        </nav>
      </aside>

      <main className="main-content">
        <header className="header">
          <h1>{activePage}</h1>
          <span>AI Smart Parking System</span>
        </header>

        {activePage === "Dashboard" ? (
          <>
            <div className="stats-grid">
              {stats.map((item) => (
                <div className="stat-card" key={item.title}>
                  <p>{item.title}</p>
                  <h2 style={{ color: item.color }}>
                    {item.value}
                  </h2>
                </div>
              ))}
            </div>

            <section className="content-card">
              <h2>Giám sát bãi đỗ xe</h2>
              <p>Camera: CAM-01</p>
              <p>Tỷ lệ lấp đầy: 60%</p>
              <p>
                Có 5 ô chưa xác định.
                Đây là dữ liệu giả lập.
              </p>
            </section>
          </>
        ) : (
          <section className="content-card">
            <h2>{activePage}</h2>
            <p>Chức năng đang được phát triển.</p>
          </section>
        )}
      </main>
    </div>
  );
}

export default App;
