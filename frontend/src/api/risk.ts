import type { AnomalyFlag, DashboardSummary, RiskScore, RiskScoreHistory } from "../types/risk";
import { apiRequest } from "./client";

export async function getLatestRiskScore(vendorId: string): Promise<RiskScore> {
  return apiRequest<RiskScore>(`/risk/vendors/${vendorId}`);
}

export async function getRiskScoreHistory(vendorId: string): Promise<RiskScoreHistory> {
  return apiRequest<RiskScoreHistory>(`/risk/vendors/${vendorId}/history`);
}

export async function computeRiskScore(vendorId: string): Promise<RiskScore> {
  return apiRequest<RiskScore>(`/risk/vendors/${vendorId}/compute`, { method: "POST" });
}

export async function getAnomaly(vendorId: string): Promise<AnomalyFlag> {
  return apiRequest<AnomalyFlag>(`/risk/vendors/${vendorId}/anomaly`);
}

export async function getDashboardSummary(): Promise<DashboardSummary> {
  return apiRequest<DashboardSummary>("/risk/dashboard/summary");
}
