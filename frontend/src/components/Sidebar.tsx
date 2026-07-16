import {
  AlertTriangle,
  Bell,
  Building2,
  ClipboardCheck,
  FileText,
  LayoutDashboard,
  LogOut,
  Network,
  ShieldCheck,
  type LucideIcon,
} from "lucide-react";
import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
  enabled: boolean;
}

const NAV_ITEMS: NavItem[] = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, enabled: true },
  { to: "/vendors", label: "Vendors", icon: Building2, enabled: true },
  { to: "/assessments", label: "Assessments", icon: ClipboardCheck, enabled: false },
  { to: "/supply-chain", label: "Supply Chain", icon: Network, enabled: false },
  { to: "/compliance", label: "Compliance", icon: ShieldCheck, enabled: false },
  { to: "/incidents", label: "Incidents", icon: AlertTriangle, enabled: false },
  { to: "/alerts", label: "Alerts", icon: Bell, enabled: false },
  { to: "/reports", label: "Reports", icon: FileText, enabled: false },
];

export function Sidebar() {
  const { sub, role, logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/login");
  }

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <div className="sidebar-brand-mark">SC</div>
        <div>
          <div className="sidebar-brand-title">SC-TPCRS</div>
          <div className="sidebar-brand-subtitle">Third-Party Risk</div>
        </div>
      </div>

      <nav className="sidebar-nav">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          if (!item.enabled) {
            return (
              <span key={item.to} className="sidebar-nav-item disabled" title="Coming soon">
                <Icon size={17} />
                {item.label}
              </span>
            );
          }
          return (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) => `sidebar-nav-item${isActive ? " active" : ""}`}
            >
              <Icon size={17} />
              {item.label}
            </NavLink>
          );
        })}
      </nav>

      <div className="sidebar-user">
        <div>
          <div className="sidebar-user-name">{sub}</div>
          <div className="sidebar-user-role">{role?.replace("_", " ")}</div>
        </div>
        <button
          className="btn-secondary"
          onClick={handleLogout}
          title="Log out"
          style={{ border: "none", background: "none", cursor: "pointer", color: "hsl(var(--muted-foreground))", padding: 4 }}
        >
          <LogOut size={16} />
        </button>
      </div>

      <div className="sidebar-footer">SC-TPCRS v1.0 · Nigerian Fintech Ecosystem · Confidential</div>
    </aside>
  );
}
