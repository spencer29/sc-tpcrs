import { Outlet } from "react-router-dom";
import { Sidebar } from "../components/Sidebar";

export function DashboardLayout() {
  return (
    <div className="app-shell">
      <Sidebar />
      <main className="page-content">
        <Outlet />
      </main>
    </div>
  );
}
