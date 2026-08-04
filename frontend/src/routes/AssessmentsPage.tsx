import { ClipboardCheck } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ApiError } from "../api/client";
import { listVendors } from "../api/vendors";
import { VendorTierBadge } from "../components/VendorTierBadge";
import type { LifecycleState, Vendor } from "../types/vendor";

// An "assessment" is a vendor sitting in one of the in-flight lifecycle
// states -- between initiation and a final onboard/reject decision. The
// vendor-service already drives this via the questionnaire + state machine;
// this page is just the work-queue view over it. Terminal states
// (INITIATED, ONBOARDED, REJECTED) are intentionally excluded.
const ASSESSMENT_STATES: { state: LifecycleState; label: string }[] = [
  { state: "QUESTIONNAIRE_SENT", label: "Questionnaire Sent" },
  { state: "QUESTIONNAIRE_COMPLETED", label: "Questionnaire Completed" },
  { state: "ASSESSMENT_IN_PROGRESS", label: "Assessment In Progress" },
];

export function AssessmentsPage() {
  const [vendors, setVendors] = useState<Vendor[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    // One request per in-flight state, merged client-side. The list
    // endpoint filters by a single state, so we fan out and combine.
    Promise.all(ASSESSMENT_STATES.map(({ state }) => listVendors({ state, size: 100 })))
      .then((responses) => {
        if (cancelled) return;
        const merged = responses.flatMap((r) => r.items);
        setVendors(merged);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof ApiError ? err.message : "Failed to load assessments");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const countFor = (state: LifecycleState) => vendors.filter((v) => v.onboarding_state === state).length;

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Assessments</h1>
        <p className="page-subtitle">
          {vendors.length} vendor{vendors.length === 1 ? "" : "s"} currently in the assessment pipeline
        </p>
      </div>

      <div className="stat-grid">
        {ASSESSMENT_STATES.map(({ state, label }) => (
          <div className="stat-tile" key={state}>
            <div className="stat-tile-label">
              {label}
              <ClipboardCheck />
            </div>
            <div className="stat-tile-value">{countFor(state)}</div>
          </div>
        ))}
      </div>

      {error && <p className="error-text">{error}</p>}

      <div className="card" style={{ marginTop: 16 }}>
        {loading ? (
          <p>Loading...</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Vendor</th>
                <th>Industry</th>
                <th>Tier</th>
                <th>Stage</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {vendors.map((vendor) => (
                <tr key={vendor.id}>
                  <td>{vendor.name}</td>
                  <td>{vendor.industry ?? "—"}</td>
                  <td>
                    <VendorTierBadge tier={vendor.overall_tier} />
                  </td>
                  <td>{vendor.onboarding_state.replaceAll("_", " ")}</td>
                  <td>
                    <Link to={`/vendors/${vendor.id}`}>Open</Link>
                  </td>
                </tr>
              ))}
              {vendors.length === 0 && (
                <tr>
                  <td colSpan={5} style={{ textAlign: "center", color: "hsl(var(--muted-foreground))" }}>
                    No vendors are currently under assessment.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
