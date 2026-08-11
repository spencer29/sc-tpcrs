import { Activity, AlertTriangle, CheckCircle2, Loader2, RefreshCw, ShieldAlert } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { ApiError } from "../api/client";
import {
  acknowledgeAlert,
  getMonitoringDashboard,
  listAlerts,
  resolveAlert,
  triggerSweep,
} from "../api/monitoring";
import { listVendors } from "../api/vendors";
import { RoleGate } from "../auth/RoleGate";
import type { AlertStatus, MonitoringAlert, MonitoringDashboard, Severity } from "../types/monitoring";

const SEVERITY_COLORS: Record<Severity, string> = {
  Critical: "hsl(0 84% 60%)",
  High: "hsl(24 95% 53%)",
  Medium: "hsl(38 92% 50%)",
  Low: "hsl(142 71% 45%)",
};

const STATUS_COLORS: Record<AlertStatus, string> = {
  open: "hsl(0 84% 60%)",
  acknowledged: "hsl(38 92% 50%)",
  resolved: "hsl(142 71% 45%)",
};

// Exposure index is 0-100 where HIGHER = worse (unlike compliance scores).
function exposureColor(index: number): string {
  if (index >= 40) return "hsl(0 84% 60%)";
  if (index >= 20) return "hsl(38 92% 50%)";
  return "hsl(142 71% 45%)";
}

const STATUS_FILTERS: (AlertStatus | "all")[] = ["all", "open", "acknowledged", "resolved"];

export function MonitoringPage() {
  const [dashboard, setDashboard] = useState<MonitoringDashboard | null>(null);
  const [alerts, setAlerts] = useState<MonitoringAlert[]>([]);
  const [vendorNames, setVendorNames] = useState<Record<string, string>>({});
  const [statusFilter, setStatusFilter] = useState<AlertStatus | "all">("open");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sweeping, setSweeping] = useState(false);
  const [sweepMsg, setSweepMsg] = useState<string | null>(null);
  const [actionId, setActionId] = useState<string | null>(null);

  function vendorLabel(id: string): string {
    return vendorNames[id] ?? `${id.slice(0, 8)}…`;
  }

  async function refresh(status: AlertStatus | "all") {
    const [dash, alertList] = await Promise.all([
      getMonitoringDashboard(),
      listAlerts(status === "all" ? {} : { status }),
    ]);
    setDashboard(dash);
    setAlerts(alertList);
  }

  useEffect(() => {
    Promise.all([getMonitoringDashboard(), listAlerts({ status: "open" }), listVendors({ size: 100 })])
      .then(([dash, alertList, vresp]) => {
        setDashboard(dash);
        setAlerts(alertList);
        setVendorNames(Object.fromEntries(vresp.items.map((v) => [v.id, v.name])));
      })
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load monitoring data"))
      .finally(() => setLoading(false));
  }, []);

  async function handleStatusFilter(status: AlertStatus | "all") {
    setStatusFilter(status);
    try {
      const alertList = await listAlerts(status === "all" ? {} : { status });
      setAlerts(alertList);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load alerts");
    }
  }

  async function handleSweep() {
    setSweeping(true);
    setSweepMsg(null);
    try {
      const result = await triggerSweep();
      setSweepMsg(
        `Swept ${result.vendors_swept} vendor(s): ${result.snapshots_written} snapshot(s), ` +
          `${result.alerts_opened} new alert(s), ${result.alerts_updated} updated (${result.duration_ms.toFixed(0)}ms).`,
      );
      await refresh(statusFilter);
    } catch (err) {
      setSweepMsg(err instanceof ApiError ? `Error: ${err.message}` : "Sweep failed");
    } finally {
      setSweeping(false);
    }
  }

  async function handleAck(alert: MonitoringAlert) {
    setActionId(alert.id);
    try {
      await acknowledgeAlert(alert.id);
      await refresh(statusFilter);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Acknowledge failed");
    } finally {
      setActionId(null);
    }
  }

  async function handleResolve(alert: MonitoringAlert) {
    setActionId(alert.id);
    try {
      await resolveAlert(alert.id);
      await refresh(statusFilter);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Resolve failed");
    } finally {
      setActionId(null);
    }
  }

  const severityOrder = useMemo(() => ["Critical", "High", "Medium", "Low"] as Severity[], []);

  return (
    <div>
      <div className="page-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "start" }}>
        <div>
          <h1 className="page-title">Continuous Monitoring &amp; Alerts</h1>
          <p className="page-subtitle">
            Real-time vendor security posture, threat-intel and cross-module alerts
          </p>
        </div>
        <RoleGate allow={["risk_officer", "ciso", "admin"]}>
          <button
            className="btn"
            onClick={handleSweep}
            disabled={sweeping}
            style={{ display: "inline-flex", alignItems: "center", gap: 6 }}
          >
            {sweeping ? <Loader2 size={15} className="spin" /> : <RefreshCw size={15} />} Sweep Now
          </button>
        </RoleGate>
      </div>

      {sweepMsg && (
        <p
          style={{
            fontSize: "0.85rem",
            marginBottom: 12,
            color: sweepMsg.startsWith("Error") ? "hsl(0 84% 60%)" : "hsl(142 71% 45%)",
          }}
        >
          {sweepMsg}
        </p>
      )}
      {error && <p className="error-text">{error}</p>}

      {loading ? (
        <p>Loading...</p>
      ) : (
        <>
          {dashboard && (
            <div className="stat-grid">
              <div className="stat-tile">
                <div className="stat-tile-label">
                  Vendors Monitored
                  <Activity />
                </div>
                <div className="stat-tile-value">{dashboard.vendors_monitored}</div>
              </div>
              <div className="stat-tile">
                <div className="stat-tile-label">
                  Open Alerts
                  <ShieldAlert />
                </div>
                <div className="stat-tile-value" style={{ color: dashboard.open_alerts > 0 ? "hsl(0 84% 60%)" : undefined }}>
                  {dashboard.open_alerts}
                </div>
              </div>
              <div className="stat-tile">
                <div className="stat-tile-label">
                  Avg Exposure Index
                  <AlertTriangle />
                </div>
                <div className="stat-tile-value" style={{ color: exposureColor(dashboard.average_exposure_index) }}>
                  {dashboard.average_exposure_index.toFixed(1)}
                </div>
              </div>
            </div>
          )}

          <div style={{ display: "grid", gridTemplateColumns: "1fr 320px", gap: 16, alignItems: "start", marginTop: 16 }}>
            <div>
              {/* Alert list */}
              <div className="card">
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                  <strong>Alerts</strong>
                  <div style={{ display: "flex", gap: 4 }}>
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
                {alerts.length === 0 ? (
                  <p style={{ color: "hsl(var(--muted-foreground))", marginTop: 8 }}>No alerts for this filter.</p>
                ) : (
                  <div style={{ marginTop: 8 }}>
                    {alerts.map((alert) => (
                      <AlertCard
                        key={alert.id}
                        alert={alert}
                        vendorLabel={vendorLabel(alert.vendor_id)}
                        busy={actionId === alert.id}
                        onAck={() => handleAck(alert)}
                        onResolve={() => handleResolve(alert)}
                      />
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Side rollups */}
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              {dashboard && (
                <>
                  <div className="card">
                    <strong>Open by Severity</strong>
                    <div style={{ display: "flex", flexDirection: "column", gap: 6, marginTop: 8 }}>
                      {severityOrder.map((sev) => (
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
                    <strong>Open by Type</strong>
                    {Object.keys(dashboard.open_by_type).length === 0 ? (
                      <p style={{ color: "hsl(var(--muted-foreground))", marginTop: 8, fontSize: "0.85rem" }}>None open.</p>
                    ) : (
                      <div style={{ display: "flex", flexDirection: "column", gap: 6, marginTop: 8, fontSize: "0.85rem" }}>
                        {Object.entries(dashboard.open_by_type).map(([type, count]) => (
                          <div key={type} style={{ display: "flex", justifyContent: "space-between" }}>
                            <span className="mono">{type}</span>
                            <strong>{count}</strong>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  <div className="card">
                    <strong>Highest Exposure</strong>
                    <p className="page-subtitle" style={{ marginTop: 2 }}>
                      Worst posture vendors
                    </p>
                    {dashboard.worst_vendors.length === 0 ? (
                      <p style={{ color: "hsl(var(--muted-foreground))", marginTop: 8, fontSize: "0.85rem" }}>
                        No snapshots yet — run a sweep.
                      </p>
                    ) : (
                      <table style={{ marginTop: 8, fontSize: "0.82rem" }}>
                        <thead>
                          <tr>
                            <th>Vendor</th>
                            <th style={{ textAlign: "right" }}>Exposure</th>
                            <th style={{ textAlign: "right" }}>Drift</th>
                          </tr>
                        </thead>
                        <tbody>
                          {dashboard.worst_vendors.map((snap) => (
                            <tr key={snap.id}>
                              <td>{vendorLabel(snap.vendor_id)}</td>
                              <td className="mono" style={{ textAlign: "right", color: exposureColor(snap.exposure_index) }}>
                                {snap.exposure_index.toFixed(1)}
                              </td>
                              <td
                                className="mono"
                                style={{ textAlign: "right", color: snap.drift > 0 ? "hsl(0 84% 60%)" : "hsl(var(--muted-foreground))" }}
                              >
                                {snap.drift > 0 ? "+" : ""}
                                {snap.drift.toFixed(1)}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    )}
                  </div>
                </>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function AlertCard({
  alert,
  vendorLabel,
  busy,
  onAck,
  onResolve,
}: {
  alert: MonitoringAlert;
  vendorLabel: string;
  busy: boolean;
  onAck: () => void;
  onResolve: () => void;
}) {
  return (
    <div
      style={{
        border: "1px solid hsl(var(--border))",
        borderRadius: 6,
        padding: 12,
        marginBottom: 8,
        borderLeftWidth: 3,
        borderLeftColor: SEVERITY_COLORS[alert.severity],
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "start", marginBottom: 4 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
          <span
            style={{
              fontSize: "0.72rem",
              padding: "1px 6px",
              borderRadius: 4,
              background: SEVERITY_COLORS[alert.severity],
              color: "white",
              fontWeight: 600,
            }}
          >
            {alert.severity}
          </span>
          <span className="mono" style={{ fontSize: "0.75rem", color: "hsl(var(--muted-foreground))" }}>
            {alert.alert_type}
          </span>
          {alert.occurrence_count > 1 && (
            <span style={{ fontSize: "0.72rem", color: "hsl(var(--muted-foreground))" }}>×{alert.occurrence_count}</span>
          )}
        </div>
        <span style={{ fontSize: "0.72rem", color: STATUS_COLORS[alert.status], fontWeight: 600, textTransform: "capitalize" }}>
          {alert.status}
        </span>
      </div>
      <div style={{ fontWeight: 500, marginBottom: 2 }}>{alert.title}</div>
      <div style={{ fontSize: "0.82rem", color: "hsl(var(--muted-foreground))", marginBottom: 6 }}>{alert.description}</div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "0.75rem" }}>
        <span style={{ color: "hsl(var(--muted-foreground))" }}>
          {vendorLabel} · {new Date(alert.last_seen_at).toLocaleString()}
        </span>
        {alert.status !== "resolved" && (
          <RoleGate allow={["risk_officer", "ciso", "admin"]}>
            <div style={{ display: "flex", gap: 6 }}>
              {alert.status === "open" && (
                <button className="btn-secondary" onClick={onAck} disabled={busy} style={{ fontSize: "0.75rem", padding: "2px 8px" }}>
                  {busy ? <Loader2 size={12} className="spin" /> : "Acknowledge"}
                </button>
              )}
              <button
                className="btn"
                onClick={onResolve}
                disabled={busy}
                style={{ fontSize: "0.75rem", padding: "2px 8px", display: "inline-flex", alignItems: "center", gap: 4 }}
              >
                <CheckCircle2 size={12} /> Resolve
              </button>
            </div>
          </RoleGate>
        )}
      </div>
    </div>
  );
}
