import type {
  AlertStatus,
  MonitoringAlert,
  MonitoringDashboard,
  MonitoringSnapshot,
  Severity,
  SweepResult,
} from "../types/monitoring";
import { apiRequest } from "./client";

export async function getMonitoringDashboard(): Promise<MonitoringDashboard> {
  return apiRequest<MonitoringDashboard>("/monitoring/dashboard");
}

export async function triggerSweep(): Promise<SweepResult> {
  return apiRequest<SweepResult>("/monitoring/sweep", { method: "POST" });
}

export async function listSnapshots(): Promise<MonitoringSnapshot[]> {
  return apiRequest<MonitoringSnapshot[]>("/monitoring/snapshots");
}

export async function listAlerts(params: {
  vendorId?: string;
  status?: AlertStatus;
  severity?: Severity;
  limit?: number;
} = {}): Promise<MonitoringAlert[]> {
  const q = new URLSearchParams();
  if (params.vendorId) q.set("vendor_id", params.vendorId);
  if (params.status) q.set("status", params.status);
  if (params.severity) q.set("severity", params.severity);
  q.set("limit", String(params.limit ?? 100));
  return apiRequest<MonitoringAlert[]>(`/monitoring/alerts?${q.toString()}`);
}

export async function acknowledgeAlert(id: string, note = ""): Promise<MonitoringAlert> {
  return apiRequest<MonitoringAlert>(`/monitoring/alerts/${id}/acknowledge`, {
    method: "POST",
    body: { note },
  });
}

export async function resolveAlert(id: string, note = ""): Promise<MonitoringAlert> {
  return apiRequest<MonitoringAlert>(`/monitoring/alerts/${id}/resolve`, {
    method: "POST",
    body: { note },
  });
}
