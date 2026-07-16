import { Plus } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ApiError } from "../api/client";
import { getLatestRiskScore } from "../api/risk";
import { listVendors } from "../api/vendors";
import { RoleGate } from "../auth/RoleGate";
import { VendorTierBadge } from "../components/VendorTierBadge";
import type { Vendor } from "../types/vendor";

function VrsCell({ vendorId }: { vendorId: string }) {
  const [vrs, setVrs] = useState<number | null | "loading">("loading");

  useEffect(() => {
    let cancelled = false;
    getLatestRiskScore(vendorId)
      .then((score) => {
        if (!cancelled) setVrs(score.vrs_score);
      })
      .catch(() => {
        if (!cancelled) setVrs(null);
      });
    return () => {
      cancelled = true;
    };
  }, [vendorId]);

  if (vrs === "loading") return <span style={{ color: "hsl(var(--muted-foreground))" }}>...</span>;
  if (vrs === null) return <span style={{ color: "hsl(var(--muted-foreground))" }}>&mdash;</span>;
  return <span className="mono">{vrs.toFixed(1)}</span>;
}

export function VendorListPage() {
  const [vendors, setVendors] = useState<Vendor[]>([]);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState("");
  const [tierFilter, setTierFilter] = useState("");
  const [stateFilter, setStateFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    listVendors({ search: search || undefined, tier: tierFilter || undefined, state: stateFilter || undefined, size: 50 })
      .then((resp) => {
        if (!cancelled) {
          setVendors(resp.items);
          setTotal(resp.total);
        }
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof ApiError ? err.message : "Failed to load vendors");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [search, tierFilter, stateFilter]);

  return (
    <div>
      <div className="page-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end" }}>
        <div>
          <h1 className="page-title">Vendors</h1>
          <p className="page-subtitle">{total} vendor{total === 1 ? "" : "s"} in the registry</p>
        </div>
        <RoleGate allow={["risk_officer", "admin"]}>
          <Link to="/vendors/new" className="btn" style={{ display: "inline-flex", alignItems: "center", gap: 6, textDecoration: "none" }}>
            <Plus size={15} /> Add Vendor
          </Link>
        </RoleGate>
      </div>

      <div className="card" style={{ marginBottom: 16, display: "flex", gap: 12 }}>
        <input placeholder="Search by name..." value={search} onChange={(e) => setSearch(e.target.value)} style={{ flex: 1 }} />
        <select value={tierFilter} onChange={(e) => setTierFilter(e.target.value)}>
          <option value="">All tiers</option>
          <option value="Critical">Critical</option>
          <option value="High">High</option>
          <option value="Medium">Medium</option>
          <option value="Low">Low</option>
        </select>
        <select value={stateFilter} onChange={(e) => setStateFilter(e.target.value)}>
          <option value="">All states</option>
          <option value="INITIATED">Initiated</option>
          <option value="QUESTIONNAIRE_SENT">Questionnaire Sent</option>
          <option value="QUESTIONNAIRE_COMPLETED">Questionnaire Completed</option>
          <option value="ASSESSMENT_IN_PROGRESS">Assessment In Progress</option>
          <option value="ONBOARDED">Onboarded</option>
          <option value="REJECTED">Rejected</option>
        </select>
      </div>

      {error && <p className="error-text">{error}</p>}

      <div className="card">
        {loading ? (
          <p>Loading...</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Industry</th>
                <th>Tier</th>
                <th>State</th>
                <th>VRS</th>
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
                    <VrsCell vendorId={vendor.id} />
                  </td>
                  <td>
                    <Link to={`/vendors/${vendor.id}`}>View</Link>
                  </td>
                </tr>
              ))}
              {vendors.length === 0 && (
                <tr>
                  <td colSpan={6} style={{ textAlign: "center", color: "hsl(var(--muted-foreground))" }}>
                    No vendors found.
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
