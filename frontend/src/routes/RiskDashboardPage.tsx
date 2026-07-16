import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getDashboardSummary } from "../api/risk";
import { ApiError } from "../api/client";
import { TierBreakdownChart } from "../components/TierBreakdownChart";
import { VrsDistributionChart } from "../components/VrsDistributionChart";
import { VendorTierBadge } from "../components/VendorTierBadge";
import type { DashboardSummary } from "../types/risk";

export function RiskDashboardPage() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    getDashboardSummary()
      .then((data) => {
        if (!cancelled) setSummary(data);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof ApiError ? err.message : "Failed to load dashboard");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (error) return <p className="error-text">{error}</p>;
  if (!summary) return <p>Loading...</p>;

  return (
    <div>
      <h1>Risk Dashboard</h1>
      <div className="grid-2">
        <div className="card">
          <h3 style={{ marginTop: 0 }}>Portfolio by Risk Tier</h3>
          <TierBreakdownChart breakdown={summary.tier_breakdown} />
        </div>
        <div className="card">
          <h3 style={{ marginTop: 0 }}>VRS Distribution</h3>
          <VrsDistributionChart distribution={summary.vrs_distribution} />
        </div>
      </div>

      <div className="card" style={{ marginTop: 16 }}>
        <h3 style={{ marginTop: 0 }}>Top Risk Vendors</h3>
        {summary.top_risk_vendors.length === 0 ? (
          <p style={{ color: "var(--text-muted)" }}>No risk scores computed yet.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Vendor</th>
                <th>VRS</th>
                <th>Tier</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {summary.top_risk_vendors.map((score) => (
                <tr key={score.vendor_id}>
                  <td>{score.vendor_id}</td>
                  <td>{score.vrs_score.toFixed(1)}</td>
                  <td>
                    <VendorTierBadge tier={score.tier} />
                  </td>
                  <td>
                    <Link to={`/vendors/${score.vendor_id}`}>View</Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
