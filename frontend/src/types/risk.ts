import type { Tier } from "./vendor";

export interface RiskScore {
  vendor_id: string;
  vrs_score: number;
  questionnaire_score: number;
  external_posture_score: number;
  vulnerability_score: number;
  breach_history_score: number;
  threat_intel_score: number;
  compliance_score: number;
  tier: Tier;
  computed_at: string;
}

export interface RiskScoreHistory {
  items: RiskScore[];
}

export interface AnomalyFlag {
  vendor_id: string;
  detected_at: string;
  anomaly_score: number;
  is_anomalous: boolean;
  model_version: string;
}

export interface DashboardSummary {
  tier_breakdown: Record<string, number>;
  vrs_distribution: Record<string, number>;
  top_risk_vendors: RiskScore[];
}
