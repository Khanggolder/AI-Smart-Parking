
function Header({ title, auth }) {
  const authText = auth.user
    ? `${auth.user.username} (${auth.role})`
    : "Chưa đăng nhập (demo)";

  return (
    <header className="header">
      <h1>{title}</h1>
      <span>{authText}</span>
    </header>
  );
}

export default Header;
