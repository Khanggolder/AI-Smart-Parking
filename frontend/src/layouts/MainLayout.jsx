
import Sidebar from "../components/Sidebar";
import Header from "../components/Header";

function MainLayout({
  activePage,
  onNavigate,
  children,
}) {
  return (
    <div className="app-container">
      <Sidebar
        activePage={activePage}
        onNavigate={onNavigate}
      />

      <main className="main-content">
        <Header title={activePage} />

        {children}
      </main>
    </div>
  );
}

export default MainLayout;
