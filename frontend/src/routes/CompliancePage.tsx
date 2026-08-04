import { FileCheck, Loader2, PlayCircle, ShieldCheck } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { ApiError } from "../api/client";
import {
  getComplianceDashboard,
  getControlLibrary,
  getGapAnalysis,
  getRegulatoryReport,
  runAssessment,
} from "../api/compliance";
import { listVendors } from "../api/vendors";
import { RoleGate } from "../auth/RoleGate";
import type {
  ComplianceDashboard,
  ControlLibrary,
  ControlResult,
  GapAnalysis,
  RegulatoryReport,
} from "../types/compliance";
import type { Vendor } from "../types/vendor";

const STATUS_COLORS: Record<string, string> = {
  Compliant: "hsl(142 71% 45%)",
  "Partially Compliant": "hsl(38 92% 50%)",
  "Non-Compliant": "hsl(0 84% 60%)",
};

function scoreColor(score: number): string {
  if (score >= 85) return "hsl(142 71% 45%)";
  if (score >= 60) return "hsl(38 92% 50%)";
  return "hsl(0 84% 60%)";
}

const CONTROL_STATUS_COLORS: Record<string, string> = {
  met: "hsl(142 71% 45%)",
  partial: "hsl(38 92% 50%)",
  gap: "hsl(0 84% 60%)",
  not_applicable: "hsl(var(--muted-foreground))",
};

export function CompliancePage() {
  const [dashboard, setDashboard] = useState<ComplianceDashboard | null>(null);
  const [library, setLibrary] = useState<ControlLibrary | null>(null);
  const [vendors, setVendors] = useState<Vendor[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // run assessment panel
  const [selectedVendor, setSelectedVendor] = useState("");
  const [selectedFramework, setSelectedFramework] = useState("ALL");
  const [running, setRunning] = useState(false);
  const [runMsg, setRunMsg] = useState<string | null>(null);

  // detail drill-down
  const [gapAnalysis, setGapAnalysis] = useState<GapAnalysis | null>(null);
  const [report, setReport] = useState<RegulatoryReport | null>(null);
  const [viewMode, setViewMode] = useState<"dashboard" | "gaps" | "report">("dashboard");

  const frameworks = useMemo(() => library?.frameworks ?? [], [library]);

  useEffect(() => {
    Promise.all([getComplianceDashboard(), getControlLibrary(), listVendors({ size: 100 })])
      .then(([dash, lib, vresp]) => {
        setDashboard(dash);
        setLibrary(lib);
        setVendors(vresp.items);
        if (vresp.items.length) setSelectedVendor(vresp.items[0].id);
      })
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load compliance data"))
      .finally(() => setLoading(false));
  }, []);

  async function handleRunAssessment() {
    if (!selectedVendor) return;
    setRunning(true);
    setRunMsg(null);
    setGapAnalysis(null);
    setReport(null);
    try {
      const assessment = await runAssessment({ vendor_id: selectedVendor, framework: selectedFramework });
      setRunMsg(
        `Assessment complete: ${assessment.status} (${assessment.compliance_score.toFixed(1)}% compliance, ` +
          `${assessment.critical_gap_count} critical gap(s)).`,
      );
      const [gaps, rpt] = await Promise.all([getGapAnalysis(assessment.id), getRegulatoryReport(assessment.id)]);
      setGapAnalysis(gaps);
      setReport(rpt);
      setViewMode("gaps");
      // refresh dashboard
      getComplianceDashboard().then(setDashboard).catch(() => undefined);
    } catch (err) {
      setRunMsg(err instanceof ApiError ? `Error: ${err.message}` : "Assessment failed");
    } finally {
      setRunning(false);
    }
  }

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Compliance</h1>
        <p className="page-subtitle">
          Automated gap analysis and regulator-ready reporting across {library?.total_controls ?? "—"} controls
        </p>
      </div>

      {error && <p className="error-text">{error}</p>}

      {loading ? (
        <p>Loading...</p>
      ) : (
        <>
          {/* Dashboard stats */}
          {dashboard && (
            <div className="stat-grid">
              <div className="stat-tile">
                <div className="stat-tile-label">
                  Vendors Assessed
                  <ShieldCheck />
                </div>
                <div className="stat-tile-value">{dashboard.vendors_assessed}</div>
              </div>
              <div className="stat-tile">
                <div className="stat-tile-label">
                  Average Score
                  <FileCheck />
                </div>
                <div className="stat-tile-value" style={{ color: scoreColor(dashboard.average_score) }}>
                  {dashboard.average_score.toFixed(1)}%
                </div>
              </div>
              <div className="stat-tile">
                <div className="stat-tile-label">Total Assessments</div>
                <div className="stat-tile-value">{dashboard.total_assessments}</div>
              </div>
            </div>
          )}

          <div style={{ display: "grid", gridTemplateColumns: "1fr 360px", gap: 16, alignItems: "start", marginTop: 16 }}>
            {/* Main content area */}
            <div>
              {viewMode === "dashboard" && dashboard && (
                <DashboardView dashboard={dashboard} frameworks={frameworks} />
              )}
              {viewMode === "gaps" && gapAnalysis && <GapAnalysisView analysis={gapAnalysis} />}
              {viewMode === "report" && report && <ReportView report={report} />}
            </div>

            {/* Side panel */}
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              <RoleGate allow={["compliance_manager", "ciso", "admin"]}>
                <div className="card">
                  <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
                    <PlayCircle size={15} />
                    <strong>Run Assessment</strong>
                  </div>
                  <label style={{ display: "block", marginBottom: 4, fontSize: "0.85rem" }}>Vendor</label>
                  <select
                    value={selectedVendor}
                    onChange={(e) => setSelectedVendor(e.target.value)}
                    style={{ width: "100%", marginBottom: 12 }}
                  >
                    {vendors.map((v) => (
                      <option key={v.id} value={v.id}>
                        {v.name}
                      </option>
                    ))}
                  </select>
                  <label style={{ display: "block", marginBottom: 4, fontSize: "0.85rem" }}>Framework</label>
                  <select
                    value={selectedFramework}
                    onChange={(e) => setSelectedFramework(e.target.value)}
                    style={{ width: "100%", marginBottom: 12 }}
                  >
                    <option value="ALL">ALL (Full Library)</option>
                    {frameworks.map((fw) => (
                      <option key={fw.framework} value={fw.framework}>
                        {fw.framework} ({fw.control_count})
                      </option>
                    ))}
                  </select>
                  <button
                    className="btn"
                    onClick={handleRunAssessment}
                    disabled={running || !selectedVendor}
                    style={{ width: "100%", display: "inline-flex", justifyContent: "center", gap: 6 }}
                  >
                    {running ? <Loader2 size={15} className="spin" /> : <PlayCircle size={15} />} Run
                  </button>
                  {runMsg && (
                    <p
                      style={{
                        fontSize: "0.8rem",
                        marginTop: 8,
                        color: runMsg.startsWith("Error") ? "hsl(0 84% 60%)" : "hsl(142 71% 45%)",
                      }}
                    >
                      {runMsg}
                    </p>
                  )}
                </div>
              </RoleGate>

              {gapAnalysis && (
                <div className="card">
                  <strong>View</strong>
                  <div style={{ display: "flex", flexDirection: "column", gap: 6, marginTop: 8 }}>
                    <button
                      className={viewMode === "gaps" ? "btn" : "btn-secondary"}
                      onClick={() => setViewMode("gaps")}
                      style={{ width: "100%", fontSize: "0.85rem" }}
                    >
                      Gap Analysis
                    </button>
                    <button
                      className={viewMode === "report" ? "btn" : "btn-secondary"}
                      onClick={() => setViewMode("report")}
                      style={{ width: "100%", fontSize: "0.85rem" }}
                    >
                      Regulatory Report
                    </button>
                    <button
                      className={viewMode === "dashboard" ? "btn" : "btn-secondary"}
                      onClick={() => setViewMode("dashboard")}
                      style={{ width: "100%", fontSize: "0.85rem" }}
                    >
                      Dashboard
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function DashboardView({ dashboard, frameworks }: { dashboard: ComplianceDashboard; frameworks: { framework: string; control_count: number }[] }) {
  return (
    <>
      <div className="card">
        <strong>Status Breakdown</strong>
        <div style={{ display: "flex", gap: 16, marginTop: 8, flexWrap: "wrap" }}>
          {Object.entries(dashboard.status_breakdown).map(([status, count]) => (
            <div key={status} style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{ width: 12, height: 12, borderRadius: "50%", background: STATUS_COLORS[status], display: "inline-block" }} />
              <span>
                {status}: <strong>{count}</strong>
              </span>
            </div>
          ))}
        </div>
      </div>

      <div className="card" style={{ marginTop: 16 }}>
        <strong>Framework Coverage</strong>
        <p className="page-subtitle" style={{ marginTop: 2 }}>
          Assessments run per framework
        </p>
        <div style={{ display: "flex", gap: 12, marginTop: 8, flexWrap: "wrap" }}>
          {frameworks.map((fw) => {
            const count = dashboard.framework_coverage[fw.framework] ?? 0;
            return (
              <div key={fw.framework} style={{ fontSize: "0.85rem" }}>
                <strong>{fw.framework}</strong>: {count}
              </div>
            );
          })}
        </div>
      </div>

      <div className="card" style={{ marginTop: 16 }}>
        <strong>Worst Performers</strong>
        <p className="page-subtitle" style={{ marginTop: 2 }}>
          Vendors with the lowest compliance scores
        </p>
        {dashboard.worst_vendors.length === 0 ? (
          <p style={{ color: "hsl(var(--muted-foreground))", marginTop: 8 }}>No assessments yet.</p>
        ) : (
          <table style={{ marginTop: 8 }}>
            <thead>
              <tr>
                <th>Framework</th>
                <th>Score</th>
                <th>Status</th>
                <th style={{ textAlign: "right" }}>Critical Gaps</th>
              </tr>
            </thead>
            <tbody>
              {dashboard.worst_vendors.map((item) => (
                <tr key={item.id}>
                  <td>{item.framework}</td>
                  <td className="mono" style={{ color: scoreColor(item.compliance_score) }}>
                    {item.compliance_score.toFixed(1)}%
                  </td>
                  <td style={{ color: STATUS_COLORS[item.status] }}>{item.status}</td>
                  <td className="mono" style={{ textAlign: "right" }}>
                    {item.critical_gap_count}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}

function GapAnalysisView({ analysis }: { analysis: GapAnalysis }) {
  return (
    <>
      <div className="card">
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
          <div>
            <strong>Gap Analysis</strong>
            <p className="page-subtitle" style={{ marginTop: 2 }}>
              {analysis.framework} — {analysis.status}
            </p>
          </div>
          <div className="mono" style={{ fontSize: "1.8rem", color: scoreColor(analysis.compliance_score) }}>
            {analysis.compliance_score.toFixed(1)}%
          </div>
        </div>
        <p style={{ fontSize: "0.85rem", marginTop: 8 }}>
          <strong>{analysis.gaps.length}</strong> gap(s) / partial compliance findings ranked by criticality
        </p>
      </div>

      <div className="card" style={{ marginTop: 16 }}>
        <strong>By Domain</strong>
        <p className="page-subtitle" style={{ marginTop: 2 }}>
          Worst-scoring domains first
        </p>
        <table style={{ marginTop: 8, fontSize: "0.85rem" }}>
          <thead>
            <tr>
              <th>Domain</th>
              <th style={{ textAlign: "right" }}>Score</th>
              <th style={{ textAlign: "right" }}>Met</th>
              <th style={{ textAlign: "right" }}>Partial</th>
              <th style={{ textAlign: "right" }}>Gap</th>
            </tr>
          </thead>
          <tbody>
            {analysis.by_domain.map((d, i) => (
              <tr key={i}>
                <td>{d.domain}</td>
                <td className="mono" style={{ textAlign: "right", color: scoreColor(d.score) }}>
                  {d.score.toFixed(0)}%
                </td>
                <td className="mono" style={{ textAlign: "right" }}>
                  {d.met}
                </td>
                <td className="mono" style={{ textAlign: "right" }}>
                  {d.partial}
                </td>
                <td className="mono" style={{ textAlign: "right" }}>
                  {d.gap}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="card" style={{ marginTop: 16 }}>
        <strong>Prioritised Gaps</strong>
        <p className="page-subtitle" style={{ marginTop: 2 }}>
          Critical gaps first, then by control weight
        </p>
        {analysis.gaps.length === 0 ? (
          <p style={{ color: "hsl(var(--muted-foreground))", marginTop: 8 }}>No gaps found.</p>
        ) : (
          <div style={{ marginTop: 8 }}>
            {analysis.gaps.map((gap, i) => (
              <ControlGapCard key={i} control={gap} />
            ))}
          </div>
        )}
      </div>
    </>
  );
}

function ControlGapCard({ control }: { control: ControlResult }) {
  return (
    <div
      style={{
        border: "1px solid hsl(var(--border))",
        borderRadius: 6,
        padding: 12,
        marginBottom: 8,
        borderLeftWidth: 3,
        borderLeftColor: control.is_critical_gap ? "hsl(0 84% 60%)" : "hsl(38 92% 50%)",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "start", marginBottom: 4 }}>
        <div>
          <span className="mono" style={{ fontSize: "0.8rem", color: "hsl(var(--muted-foreground))" }}>
            {control.reference}
          </span>
          {control.is_critical_gap && (
            <span style={{ marginLeft: 8, fontSize: "0.75rem", color: "hsl(0 84% 60%)", fontWeight: 600 }}>CRITICAL</span>
          )}
        </div>
        <span
          style={{
            fontSize: "0.75rem",
            padding: "2px 6px",
            borderRadius: 4,
            background: CONTROL_STATUS_COLORS[control.status],
            color: "white",
          }}
        >
          {control.status}
        </span>
      </div>
      <div style={{ fontWeight: 500, marginBottom: 4 }}>{control.title}</div>
      <div style={{ fontSize: "0.82rem", color: "hsl(var(--muted-foreground))", marginBottom: 6 }}>{control.domain}</div>
      {control.evidence && (
        <div style={{ fontSize: "0.8rem", marginTop: 6 }}>
          <strong>Evidence:</strong> {control.evidence}
        </div>
      )}
      {control.remediation && (
        <div style={{ fontSize: "0.8rem", marginTop: 4 }}>
          <strong>Remediation:</strong> {control.remediation}
        </div>
      )}
    </div>
  );
}

function ReportView({ report }: { report: RegulatoryReport }) {
  return (
    <>
      <div className="card">
        <strong>Regulatory Report</strong>
        <p className="page-subtitle" style={{ marginTop: 2 }}>
          Generated {new Date(report.generated_at).toLocaleString()}
        </p>
        <div style={{ marginTop: 12, fontSize: "0.85rem", lineHeight: 1.6, whiteSpace: "pre-wrap" }}>{report.attestation}</div>
      </div>

      <div className="card" style={{ marginTop: 16 }}>
        <strong>Assessment Summary</strong>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 12, marginTop: 8, fontSize: "0.85rem" }}>
          <div>
            <div style={{ color: "hsl(var(--muted-foreground))" }}>Framework</div>
            <div style={{ fontWeight: 500 }}>{report.assessment.framework}</div>
          </div>
          <div>
            <div style={{ color: "hsl(var(--muted-foreground))" }}>Compliance Score</div>
            <div className="mono" style={{ fontWeight: 500, color: scoreColor(report.assessment.compliance_score) }}>
              {report.assessment.compliance_score.toFixed(1)}%
            </div>
          </div>
          <div>
            <div style={{ color: "hsl(var(--muted-foreground))" }}>Total Controls</div>
            <div className="mono">{report.assessment.total_controls}</div>
          </div>
          <div>
            <div style={{ color: "hsl(var(--muted-foreground))" }}>Critical Gaps</div>
            <div className="mono">{report.assessment.critical_gap_count}</div>
          </div>
        </div>
      </div>

      <div className="card" style={{ marginTop: 16 }}>
        <strong>Control Register</strong>
        <p className="page-subtitle" style={{ marginTop: 2 }}>
          Full control-by-control assessment ({report.control_register.length} controls)
        </p>
        <div style={{ maxHeight: 400, overflow: "auto", marginTop: 8 }}>
          <table style={{ fontSize: "0.8rem" }}>
            <thead>
              <tr>
                <th>Reference</th>
                <th>Title</th>
                <th>Status</th>
                <th style={{ textAlign: "center" }}>Weight</th>
              </tr>
            </thead>
            <tbody>
              {report.control_register.map((c, i) => (
                <tr key={i}>
                  <td className="mono">{c.reference}</td>
                  <td>{c.title.length > 50 ? `${c.title.slice(0, 50)}…` : c.title}</td>
                  <td style={{ color: CONTROL_STATUS_COLORS[c.status] }}>{c.status}</td>
                  <td className="mono" style={{ textAlign: "center" }}>
                    {c.weight}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
