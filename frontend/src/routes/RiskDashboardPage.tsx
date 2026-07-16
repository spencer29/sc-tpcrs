import { AlertTriangle, Building2, ShieldAlert, TrendingUp } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ApiError } from "../api/client";
import { getDashboardSummary } from "../api/risk";
import { listVendors } from "../api/vendors";
import { TierBreakdownChart } from "../components/TierBreakdownChart";
import { VendorTierBadge } from "../components/VendorTierBadge";
import { VrsDistributionChart } from "../components/VrsDistributionChart";
import type { DashboardSummary } from "../types/risk";

export function RiskDashboardPage() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [totalVendors, setTotalVendors] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    Promise.all([getDashboardSummary(), listVendors({ size: 1 })])
      .then(([summaryData, vendorList]) => {
        if (!cancelled) {
          setSummary(summaryData);
          setTotalVendors(vendorList.total);
        }
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

  const criticalCount = summary.tier_breakdown["Critical"] ?? 0;
  const highCount = summary.tier_breakdown["High"] ?? 0;
  const scoredCount = Object.values(summary.tier_breakdown).reduce((sum, n) => sum + n, 0);

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Executive Risk Dashboard</h1>
        <p className="page-subtitle">Portfolio-wide vendor risk posture, updated in real time as assessments complete.</p>
      </div>

      <div className="stat-grid">
        <div className="stat-tile">
          <div className="stat-tile-label">
            Total Vendors
            <Building2 />
          </div>
          <div className="stat-tile-value">{totalVendors ?? "—"}</div>
        </div>
        <div className="stat-tile">
          <div className="stat-tile-label">
            Critical Tier
            <ShieldAlert />
          </div>
          <div className="stat-tile-value">{criticalCount}</div>
        </div>
        <div className="stat-tile">
          <div className="stat-tile-label">
            High Tier
            <AlertTriangle />
          </div>
          <div className="stat-tile-value">{highCount}</div>
        </div>
        <div className="stat-tile">
          <div className="stat-tile-label">
            Vendors Scored
            <TrendingUp />
          </div>
          <div className="stat-tile-value">{scoredCount}</div>
        </div>
      </div>

      <div className="grid-2">
        <div className="card">
          <h3 className="card-title">Portfolio Risk Summary</h3>
          <p className="card-description">Vendor count by current risk tier</p>
          <TierBreakdownChart breakdown={summary.tier_breakdown} />
        </div>
        <div className="card">
          <h3 className="card-title">Risk Score Distribution</h3>
          <p className="card-description">Vendor Risk Score (VRS) buckets across the portfolio</p>
          <VrsDistributionChart distribution={summary.vrs_distribution} />
        </div>
      </div>

      <div className="card" style={{ marginTop: 16 }}>
        <h3 className="card-title">Top Risk Vendors</h3>
        <p className="card-description">Highest current VRS across the portfolio</p>
        {summary.top_risk_vendors.length === 0 ? (
          <p style={{ color: "hsl(var(--muted-foreground))" }}>No risk scores computed yet.</p>
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
                  <td className="mono">{score.vendor_id}</td>
                  <td className="mono">{score.vrs_score.toFixed(1)}</td>
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
