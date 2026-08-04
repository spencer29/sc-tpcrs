import type {
  Assessment,
  AssessmentListItem,
  AssessmentRequest,
  ComplianceDashboard,
  ControlLibrary,
  Control,
  ControlResult,
  ControlStatus,
  GapAnalysis,
  RegulatoryReport,
} from "../types/compliance";
import { apiRequest } from "./client";

export async function getControlLibrary(): Promise<ControlLibrary> {
  return apiRequest<ControlLibrary>("/compliance/controls");
}

export async function listControls(framework?: string): Promise<Control[]> {
  const q = framework ? `?framework=${encodeURIComponent(framework)}` : "";
  return apiRequest<Control[]>(`/compliance/controls/list${q}`);
}

export async function runAssessment(body: AssessmentRequest): Promise<Assessment> {
  return apiRequest<Assessment>("/compliance/assessments", { method: "POST", body });
}

export async function listAssessments(vendorId?: string, limit = 50): Promise<AssessmentListItem[]> {
  const params = new URLSearchParams();
  if (vendorId) params.set("vendor_id", vendorId);
  params.set("limit", String(limit));
  return apiRequest<AssessmentListItem[]>(`/compliance/assessments?${params.toString()}`);
}

export async function getAssessment(id: string): Promise<Assessment> {
  return apiRequest<Assessment>(`/compliance/assessments/${id}`);
}

export async function getGapAnalysis(id: string): Promise<GapAnalysis> {
  return apiRequest<GapAnalysis>(`/compliance/assessments/${id}/gap-analysis`);
}

export async function getRegulatoryReport(id: string): Promise<RegulatoryReport> {
  return apiRequest<RegulatoryReport>(`/compliance/assessments/${id}/report`);
}

export async function getAssessmentControls(id: string, status?: ControlStatus): Promise<ControlResult[]> {
  const q = status ? `?status=${status}` : "";
  return apiRequest<ControlResult[]>(`/compliance/assessments/${id}/controls${q}`);
}

export async function getComplianceDashboard(): Promise<ComplianceDashboard> {
  return apiRequest<ComplianceDashboard>("/compliance/dashboard");
}
