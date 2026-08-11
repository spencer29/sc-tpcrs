export type Severity = "Critical" | "High" | "Medium" | "Low";
export type AlertStatus = "open" | "acknowledged" | "resolved";

export interface MonitoringSnapshot {
  id: string;
  vendor_id: string;
  posture_score: number;
  open_service_count: number;
  ioc_match_count: number;
  abuse_report_count: number;
  exposure_index: number;
  drift: number;
  observed_at: string;
}

export interface MonitoringAlert {
  id: string;
  vendor_id: string;
  alert_type: string;
  severity: Severity;
  title: string;
  description: string;
  status: AlertStatus;
  source: string;
  details: Record<string, unknown>;
  occurrence_count: number;
  first_seen_at: string;
  last_seen_at: string;
  acknowledged_by?: string | null;
  acknowledged_at?: string | null;
  resolved_at?: string | null;
}

export interface SweepResult {
  vendors_swept: number;
  snapshots_written: number;
  alerts_opened: number;
  alerts_updated: number;
  duration_ms: number;
}

export interface MonitoringDashboard {
  vendors_monitored: number;
  open_alerts: number;
  open_by_severity: Record<string, number>;
  open_by_type: Record<string, number>;
  average_exposure_index: number;
  worst_vendors: MonitoringSnapshot[];
  recent_alerts: MonitoringAlert[];
}
