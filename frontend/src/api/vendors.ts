import type { Answer, Questionnaire, Vendor, VendorDocument, VendorListResponse } from "../types/vendor";
import { apiRequest } from "./client";

export interface VendorFilters {
  tier?: string;
  state?: string;
  search?: string;
  page?: number;
  size?: number;
}

export async function listVendors(filters: VendorFilters = {}): Promise<VendorListResponse> {
  const params = new URLSearchParams();
  if (filters.tier) params.set("tier", filters.tier);
  if (filters.state) params.set("state", filters.state);
  if (filters.search) params.set("search", filters.search);
  params.set("page", String(filters.page ?? 1));
  params.set("size", String(filters.size ?? 20));
  return apiRequest<VendorListResponse>(`/vendors?${params.toString()}`);
}

export async function getVendor(id: string): Promise<Vendor> {
  return apiRequest<Vendor>(`/vendors/${id}`);
}

export interface VendorCreateInput {
  name: string;
  legal_entity_name?: string;
  country?: string;
  industry?: string;
  contact_name?: string;
  contact_email?: string;
  data_access_scope: string;
  service_criticality: string;
  integration_depth: string;
}

export async function createVendor(input: VendorCreateInput): Promise<Vendor> {
  return apiRequest<Vendor>("/vendors", { method: "POST", body: input });
}

export async function transitionVendor(id: string, targetState: string): Promise<Vendor> {
  return apiRequest<Vendor>(`/vendors/${id}/transition`, { method: "POST", body: { target_state: targetState } });
}

export async function generateQuestionnaire(vendorId: string): Promise<Questionnaire> {
  return apiRequest<Questionnaire>(`/vendors/${vendorId}/questionnaire`, { method: "POST" });
}

export async function getQuestionnaire(vendorId: string): Promise<Questionnaire> {
  return apiRequest<Questionnaire>(`/vendors/${vendorId}/questionnaire`);
}

export async function submitQuestionnaireResponses(
  vendorId: string,
  responses: { question_code: string; answer: Answer }[],
): Promise<Questionnaire> {
  return apiRequest<Questionnaire>(`/vendors/${vendorId}/questionnaire/responses`, {
    method: "PUT",
    body: { responses },
  });
}

export async function listDocuments(vendorId: string): Promise<VendorDocument[]> {
  return apiRequest<VendorDocument[]>(`/vendors/${vendorId}/documents`);
}
