import type {
  Incident,
  IncidentCategory,
  IncidentDashboard,
  IncidentDetail,
  IncidentNotification,
  IncidentStatus,
  Severity,
  TimelineEntry,
} from "../types/incident";
import { apiRequest } from "./client";

export async function getIncidentDashboard(): Promise<IncidentDashboard> {
  return apiRequest<IncidentDashboard>("/incidents/dashboard");
}

export async function listIncidents(params: {
  vendorId?: string;
  status?: IncidentStatus;
  severity?: Severity;
  limit?: number;
} = {}): Promise<Incident[]> {
  const q = new URLSearchParams();
  if (params.vendorId) q.set("vendor_id", params.vendorId);
  if (params.status) q.set("status", params.status);
  if (params.severity) q.set("severity", params.severity);
  q.set("limit", String(params.limit ?? 100));
  return apiRequest<Incident[]>(`/incidents?${q.toString()}`);
}

export async function getIncident(id: string): Promise<IncidentDetail> {
  return apiRequest<IncidentDetail>(`/incidents/${id}`);
}

export interface CreateIncidentInput {
  vendor_id: string;
  title: string;
  description?: string;
  severity?: Severity;
  category?: IncidentCategory;
  personal_data_involved?: boolean;
}

export async function createIncident(body: CreateIncidentInput): Promise<IncidentDetail> {
  return apiRequest<IncidentDetail>("/incidents", { method: "POST", body });
}

export async function updateIncidentStatus(
  id: string,
  status: IncidentStatus,
  note = "",
): Promise<IncidentDetail> {
  return apiRequest<IncidentDetail>(`/incidents/${id}/status`, {
    method: "POST",
    body: { status, note },
  });
}

export async function assignIncident(id: string, assignee: string, note = ""): Promise<IncidentDetail> {
  return apiRequest<IncidentDetail>(`/incidents/${id}/assign`, {
    method: "POST",
    body: { assignee, note },
  });
}

export async function addIncidentNote(id: string, message: string): Promise<IncidentDetail> {
  return apiRequest<IncidentDetail>(`/incidents/${id}/notes`, {
    method: "POST",
    body: { message },
  });
}

export async function getIncidentTimeline(id: string): Promise<TimelineEntry[]> {
  return apiRequest<TimelineEntry[]>(`/incidents/${id}/timeline`);
}

export async function getIncidentNotifications(id: string): Promise<IncidentNotification[]> {
  return apiRequest<IncidentNotification[]>(`/incidents/${id}/notifications`);
}
