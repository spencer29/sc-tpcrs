import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

export function NavBar() {
  const { sub, role, logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/login");
  }

  return (
    <nav className="navbar">
      <div className="navbar-brand">SC-TPCRS</div>
      <div className="navbar-links">
        <NavLink to="/" end className={({ isActive }) => (isActive ? "active" : "")}>
          Dashboard
        </NavLink>
        <NavLink to="/vendors" className={({ isActive }) => (isActive ? "active" : "")}>
          Vendors
        </NavLink>
      </div>
      <div className="navbar-user">
        <span>
          {sub} ({role})
        </span>
        <button className="btn btn-secondary" onClick={handleLogout}>
          Log out
        </button>
      </div>
    </nav>
  );
}
