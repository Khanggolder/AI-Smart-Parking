
import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { CarFront, LockKeyhole } from "lucide-react";

function Login({ onLogin }) {
  const navigate = useNavigate();
  const location = useLocation();

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setLoading(true);

    try {
      await onLogin(username.trim(), password);

      const destination = location.state?.from || "/";
      navigate(destination, { replace: true });
    } catch (err) {
      if (!err.response) {
        setError(
          err.message === "Network Error"
            ? "Không kết nối được Backend. Hãy kiểm tra API."
            : err.message || "Không thể đăng nhập."
        );
      } else if (err.response.status === 401) {
        setError("Tên đăng nhập hoặc mật khẩu không đúng.");
      } else {
        setError(
          err.response.data?.error?.message ||
          "Đăng nhập thất bại. Vui lòng thử lại."
        );
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="login-page">
      <section className="login-card">
        <div className="login-logo">
          <CarFront size={30} />
        </div>

        <h1>AI Smart Parking</h1>
        <p className="login-subtitle">
          Đăng nhập hệ thống quản lý bãi đỗ xe
        </p>

        <form onSubmit={handleSubmit}>
          <label htmlFor="username">
            Tên đăng nhập
          </label>
          <input
            id="username"
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="Nhập tên đăng nhập"
            autoComplete="username"
            required
          />

          <label htmlFor="password">
            Mật khẩu
          </label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Nhập mật khẩu"
            autoComplete="current-password"
            required
          />

          {error && (
            <p className="login-error" role="alert">
              {error}
            </p>
          )}

          <button
            className="login-button"
            type="submit"
            disabled={loading}
          >
            <LockKeyhole size={18} />
            {loading ? "Đang đăng nhập..." : "Đăng nhập"}
          </button>
        </form>

        <p className="login-footer">
          Tài khoản được quản lý bởi quản trị viên.
        </p>
      </section>
    </main>
  );
}

export default Login;
