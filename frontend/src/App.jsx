
import { useState } from "react";

import MainLayout from "./layouts/MainLayout";
import Dashboard from "./pages/Dashboard";

import "./App.css";

function App() {
  const [activePage, setActivePage] = useState("Dashboard");

  function renderPage() {
    switch (activePage) {
      case "Dashboard":
        return <Dashboard />;

      default:
        return (
          <section className="content-card">
            <h2>{activePage}</h2>
            <p>Chức năng đang được phát triển.</p>
          </section>
        );
    }
  }

  return (
    <MainLayout
      activePage={activePage}
      onNavigate={setActivePage}
    >
      {renderPage()}
    </MainLayout>
  );
}

export default App;
