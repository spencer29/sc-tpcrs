import { Outlet } from "react-router-dom";
import { NavBar } from "../components/NavBar";

export function DashboardLayout() {
  return (
    <div className="app-shell">
      <NavBar />
      <main className="page-content">
        <Outlet />
      </main>
    </div>
  );
}
