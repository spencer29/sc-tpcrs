export type Severity = "Critical" | "High" | "Medium" | "Low";
export type IncidentStatus = "open" | "investigating" | "contained" | "resolved" | "closed";
export type IncidentCategory =
  | "SECURITY_POSTURE"
  | "THREAT_INTEL"
  | "VULNERABILITY"
  | "COMPLIANCE"
  | "RISK"
  | "DATA_BREACH"
  | "MANUAL";

export interface TimelineEntry {
  id: string;
  incident_id: string;
  event_type: string;
  actor: string;
  message: string;
  from_status?: string | null;
  to_status?: string | null;
  created_at: string;
}

export interface IncidentNotification {
  id: string;
  incident_id: string;
  regulator: string;
  status: string;
  deadline_at: string;
  body: string;
  reference?: string | null;
  created_at: string;
  submitted_at?: string | null;
}

export interface Incident {
  id: string;
  reference: string;
  vendor_id: string;
  title: string;
  description: string;
  severity: Severity;
  status: IncidentStatus;
  category: string;
  source: string;
  source_ref?: string | null;
  assignee?: string | null;
  sla_due_at: string;
  sla_breached: boolean;
  requires_cbn_notification: boolean;
  requires_ndpa_notification: boolean;
  opened_at: string;
  updated_at: string;
  contained_at?: string | null;
  resolved_at?: string | null;
  closed_at?: string | null;
}

export interface IncidentDetail extends Incident {
  timeline: TimelineEntry[];
  notifications: IncidentNotification[];
}

export interface IncidentDashboard {
  total_incidents: number;
  open_incidents: number;
  open_by_severity: Record<string, number>;
  open_by_category: Record<string, number>;
  sla_breached: number;
  pending_notifications: number;
  mean_time_to_contain_hours?: number | null;
  recent_incidents: Incident[];
}
