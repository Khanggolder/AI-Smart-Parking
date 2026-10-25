
import { LogOut } from "lucide-react";

function Header({ title, auth, onLogout }) {
  return (
    <header className="header">
      <h1>{title}</h1>

      <div className="header-user">
        <span>
          {auth.user?.username || "Người dùng"}
          {" · "}
          {auth.role === "admin" ? "Admin" : "Operator"}
        </span>

        <button
          type="button"
          className="logout-button"
          onClick={onLogout}
        >
          <LogOut size={16} />
          Đăng xuất
        </button>
      </div>
    </header>
  );
}

export default Header;
