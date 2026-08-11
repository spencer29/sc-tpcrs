import { AlertTriangle, Clock, FileWarning, Loader2, ShieldAlert } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { ApiError } from "../api/client";
import {
  getIncident,
  getIncidentDashboard,
  listIncidents,
  updateIncidentStatus,
} from "../api/incidents";
import { listVendors } from "../api/vendors";
import { RoleGate } from "../auth/RoleGate";
import type {
  Incident,
  IncidentDashboard,
  IncidentDetail,
  IncidentStatus,
  Severity,
} from "../types/incident";

const SEVERITY_COLORS: Record<Severity, string> = {
  Critical: "hsl(0 84% 60%)",
  High: "hsl(24 95% 53%)",
  Medium: "hsl(38 92% 50%)",
  Low: "hsl(142 71% 45%)",
};

const STATUS_COLORS: Record<IncidentStatus, string> = {
  open: "hsl(0 84% 60%)",
  investigating: "hsl(24 95% 53%)",
  contained: "hsl(38 92% 50%)",
  resolved: "hsl(142 71% 45%)",
  closed: "hsl(var(--muted-foreground))",
};

// Allowed next states mirror the backend lifecycle state machine.
const NEXT_STATES: Record<IncidentStatus, IncidentStatus[]> = {
  open: ["investigating", "contained", "resolved", "closed"],
  investigating: ["contained", "resolved", "closed"],
  contained: ["resolved", "investigating", "closed"],
  resolved: ["closed", "investigating"],
  closed: [],
};

const STATUS_FILTERS: (IncidentStatus | "all")[] = [
  "all",
  "open",
  "investigating",
  "contained",
  "resolved",
  "closed",
];

const SEVERITY_ORDER: Severity[] = ["Critical", "High", "Medium", "Low"];

export function IncidentsPage() {
  const [dashboard, setDashboard] = useState<IncidentDashboard | null>(null);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [vendorNames, setVendorNames] = useState<Record<string, string>>({});
  const [statusFilter, setStatusFilter] = useState<IncidentStatus | "all">("all");
  const [selected, setSelected] = useState<IncidentDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionId, setActionId] = useState<string | null>(null);

  function vendorLabel(id: string): string {
    return vendorNames[id] ?? `${id.slice(0, 8)}…`;
  }

  async function refresh(status: IncidentStatus | "all") {
    const [dash, list] = await Promise.all([
      getIncidentDashboard(),
      listIncidents(status === "all" ? {} : { status }),
    ]);
    setDashboard(dash);
    setIncidents(list);
  }

  useEffect(() => {
    Promise.all([getIncidentDashboard(), listIncidents(), listVendors({ size: 100 })])
      .then(([dash, list, vresp]) => {
        setDashboard(dash);
        setIncidents(list);
        setVendorNames(Object.fromEntries(vresp.items.map((v) => [v.id, v.name])));
      })
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load incidents"))
      .finally(() => setLoading(false));
  }, []);

  async function handleStatusFilter(status: IncidentStatus | "all") {
    setStatusFilter(status);
    try {
      setIncidents(await listIncidents(status === "all" ? {} : { status }));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load incidents");
    }
  }

  async function openDetail(id: string) {
    try {
      setSelected(await getIncident(id));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load incident");
    }
  }

  async function handleTransition(incident: Incident, status: IncidentStatus) {
    setActionId(incident.id);
    try {
      const updated = await updateIncidentStatus(incident.id, status);
      setSelected(updated);
      await refresh(statusFilter);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Status change failed");
    } finally {
      setActionId(null);
    }
  }

  const mttc = useMemo(
    () => (dashboard?.mean_time_to_contain_hours ?? null),
    [dashboard],
  );

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Incident Response</h1>
        <p className="page-subtitle">
          Third-party incidents auto-opened from monitoring alerts, with lifecycle, SLA and
          Nigerian regulatory notifications (CBN, NDPC)
        </p>
      </div>

      {error && <p className="error-text">{error}</p>}

      {loading ? (
        <p>Loading...</p>
      ) : (
        <>
          {dashboard && (
            <div className="stat-grid">
              <div className="stat-tile">
                <div className="stat-tile-label">
                  Open Incidents
                  <ShieldAlert />
                </div>
                <div className="stat-tile-value">{dashboard.open_incidents}</div>
              </div>
              <div className="stat-tile">
                <div className="stat-tile-label">
                  SLA Breached
                  <Clock />
                </div>
                <div
                  className="stat-tile-value"
                  style={{ color: dashboard.sla_breached > 0 ? "hsl(0 84% 60%)" : undefined }}
                >
                  {dashboard.sla_breached}
                </div>
              </div>
              <div className="stat-tile">
                <div className="stat-tile-label">
                  Pending Notifications
                  <FileWarning />
                </div>
                <div
                  className="stat-tile-value"
                  style={{ color: dashboard.pending_notifications > 0 ? "hsl(38 92% 50%)" : undefined }}
                >
                  {dashboard.pending_notifications}
                </div>
              </div>
              <div className="stat-tile">
                <div className="stat-tile-label">
                  Mean Time to Contain
                  <AlertTriangle />
                </div>
                <div className="stat-tile-value">{mttc === null ? "—" : `${mttc.toFixed(1)}h`}</div>
              </div>
            </div>
          )}

          <div
            style={{
              display: "grid",
              gridTemplateColumns: selected ? "1fr 420px" : "1fr",
              gap: 16,
              alignItems: "start",
              marginTop: 16,
            }}
          >
            <div className="card">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                <strong>Incidents</strong>
                <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
                  {STATUS_FILTERS.map((s) => (
                    <button
                      key={s}
                      className={statusFilter === s ? "btn" : "btn-secondary"}
                      onClick={() => handleStatusFilter(s)}
                      style={{ fontSize: "0.75rem", padding: "2px 8px", textTransform: "capitalize" }}
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>
              {incidents.length === 0 ? (
                <p style={{ color: "hsl(var(--muted-foreground))", marginTop: 8 }}>No incidents for this filter.</p>
              ) : (
                <table style={{ marginTop: 8, fontSize: "0.85rem", width: "100%" }}>
                  <thead>
                    <tr>
                      <th>Ref</th>
                      <th>Title</th>
                      <th>Vendor</th>
                      <th>Severity</th>
                      <th>Status</th>
                      <th>SLA</th>
                    </tr>
                  </thead>
                  <tbody>
                    {incidents.map((inc) => (
                      <tr
                        key={inc.id}
                        onClick={() => openDetail(inc.id)}
                        style={{ cursor: "pointer", background: selected?.id === inc.id ? "hsl(var(--muted))" : undefined }}
                      >
                        <td className="mono">{inc.reference}</td>
                        <td>{inc.title}</td>
                        <td>{vendorLabel(inc.vendor_id)}</td>
                        <td>
                          <span style={{ color: SEVERITY_COLORS[inc.severity], fontWeight: 600 }}>{inc.severity}</span>
                        </td>
                        <td>
                          <span style={{ color: STATUS_COLORS[inc.status], fontWeight: 600, textTransform: "capitalize" }}>
                            {inc.status}
                          </span>
                        </td>
                        <td>
                          {inc.sla_breached ? (
                            <span style={{ color: "hsl(0 84% 60%)", fontWeight: 600 }}>Breached</span>
                          ) : (
                            <span style={{ color: "hsl(var(--muted-foreground))" }}>On track</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>

            {selected && (
              <IncidentDetailPanel
                incident={selected}
                vendorLabel={vendorLabel(selected.vendor_id)}
                busy={actionId === selected.id}
                onClose={() => setSelected(null)}
                onTransition={(status) => handleTransition(selected, status)}
              />
            )}
          </div>

          {dashboard && !selected && <SeverityRollup dashboard={dashboard} />}
        </>
      )}
    </div>
  );
}

function SeverityRollup({ dashboard }: { dashboard: IncidentDashboard }) {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginTop: 16 }}>
      <div className="card">
        <strong>Open by Severity</strong>
        <div style={{ display: "flex", flexDirection: "column", gap: 6, marginTop: 8 }}>
          {SEVERITY_ORDER.map((sev) => (
            <div key={sev} style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
                <span style={{ width: 10, height: 10, borderRadius: "50%", background: SEVERITY_COLORS[sev] }} />
                {sev}
              </span>
              <strong>{dashboard.open_by_severity[sev] ?? 0}</strong>
            </div>
          ))}
        </div>
      </div>
      <div className="card">
        <strong>Open by Category</strong>
        {Object.keys(dashboard.open_by_category).length === 0 ? (
          <p style={{ color: "hsl(var(--muted-foreground))", marginTop: 8, fontSize: "0.85rem" }}>None open.</p>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 6, marginTop: 8, fontSize: "0.85rem" }}>
            {Object.entries(dashboard.open_by_category).map(([cat, count]) => (
              <div key={cat} style={{ display: "flex", justifyContent: "space-between" }}>
                <span className="mono">{cat}</span>
                <strong>{count}</strong>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function IncidentDetailPanel({
  incident,
  vendorLabel,
  busy,
  onClose,
  onTransition,
}: {
  incident: IncidentDetail;
  vendorLabel: string;
  busy: boolean;
  onClose: () => void;
  onTransition: (status: IncidentStatus) => void;
}) {
  return (
    <div className="card" style={{ position: "sticky", top: 16 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "start", marginBottom: 8 }}>
        <div>
          <div className="mono" style={{ fontSize: "0.8rem", color: "hsl(var(--muted-foreground))" }}>
            {incident.reference}
          </div>
          <strong>{incident.title}</strong>
        </div>
        <button className="btn-secondary" onClick={onClose} style={{ fontSize: "0.75rem", padding: "2px 8px" }}>
          Close
        </button>
      </div>

      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 8 }}>
        <span
          style={{
            fontSize: "0.72rem",
            padding: "1px 6px",
            borderRadius: 4,
            background: SEVERITY_COLORS[incident.severity],
            color: "white",
            fontWeight: 600,
          }}
        >
          {incident.severity}
        </span>
        <span style={{ fontSize: "0.72rem", color: STATUS_COLORS[incident.status], fontWeight: 600, textTransform: "capitalize" }}>
          {incident.status}
        </span>
        <span className="mono" style={{ fontSize: "0.72rem", color: "hsl(var(--muted-foreground))" }}>
          {incident.category}
        </span>
      </div>

      <p style={{ fontSize: "0.85rem", color: "hsl(var(--muted-foreground))" }}>{incident.description}</p>

      <dl style={{ fontSize: "0.82rem", marginTop: 8 }}>
        <div style={{ display: "flex", justifyContent: "space-between" }}>
          <dt style={{ color: "hsl(var(--muted-foreground))" }}>Vendor</dt>
          <dd>{vendorLabel}</dd>
        </div>
        <div style={{ display: "flex", justifyContent: "space-between" }}>
          <dt style={{ color: "hsl(var(--muted-foreground))" }}>Source</dt>
          <dd className="mono">{incident.source}</dd>
        </div>
        <div style={{ display: "flex", justifyContent: "space-between" }}>
          <dt style={{ color: "hsl(var(--muted-foreground))" }}>SLA due</dt>
          <dd style={{ color: incident.sla_breached ? "hsl(0 84% 60%)" : undefined }}>
            {new Date(incident.sla_due_at).toLocaleString()}
          </dd>
        </div>
        {incident.assignee && (
          <div style={{ display: "flex", justifyContent: "space-between" }}>
            <dt style={{ color: "hsl(var(--muted-foreground))" }}>Assignee</dt>
            <dd>{incident.assignee}</dd>
          </div>
        )}
      </dl>

      <RoleGate allow={["risk_officer", "ciso", "admin"]}>
        {NEXT_STATES[incident.status].length > 0 && (
          <div style={{ marginTop: 8 }}>
            <div style={{ fontSize: "0.78rem", color: "hsl(var(--muted-foreground))", marginBottom: 4 }}>
              Advance status
            </div>
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
              {NEXT_STATES[incident.status].map((next) => (
                <button
                  key={next}
                  className="btn-secondary"
                  disabled={busy}
                  onClick={() => onTransition(next)}
                  style={{ fontSize: "0.75rem", padding: "2px 8px", textTransform: "capitalize" }}
                >
                  {busy ? <Loader2 size={12} className="spin" /> : next}
                </button>
              ))}
            </div>
          </div>
        )}
      </RoleGate>

      {incident.notifications.length > 0 && (
        <div style={{ marginTop: 12 }}>
          <strong style={{ fontSize: "0.85rem" }}>Regulatory Notifications</strong>
          {incident.notifications.map((n) => (
            <details key={n.id} style={{ marginTop: 6, fontSize: "0.8rem" }}>
              <summary style={{ cursor: "pointer" }}>
                <span style={{ fontWeight: 600 }}>{n.regulator}</span> · {n.status} · due{" "}
                {new Date(n.deadline_at).toLocaleString()}
              </summary>
              <pre
                style={{
                  whiteSpace: "pre-wrap",
                  fontSize: "0.75rem",
                  background: "hsl(var(--muted))",
                  padding: 8,
                  borderRadius: 4,
                  marginTop: 4,
                }}
              >
                {n.body}
              </pre>
            </details>
          ))}
        </div>
      )}

      <div style={{ marginTop: 12 }}>
        <strong style={{ fontSize: "0.85rem" }}>Timeline</strong>
        <ul style={{ listStyle: "none", padding: 0, marginTop: 6, fontSize: "0.8rem" }}>
          {incident.timeline.map((t) => (
            <li key={t.id} style={{ paddingBottom: 6, borderLeft: "2px solid hsl(var(--border))", paddingLeft: 8, marginLeft: 4 }}>
              <div style={{ color: "hsl(var(--muted-foreground))", fontSize: "0.72rem" }}>
                {new Date(t.created_at).toLocaleString()} · {t.actor}
              </div>
              <div>
                <span className="mono" style={{ fontSize: "0.72rem" }}>
                  {t.event_type}
                </span>{" "}
                {t.message}
              </div>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
