import type {
  CriticalPathVendor,
  IngestResponse,
  SbomComponent,
  SbomDocument,
  SbomVulnerability,
  SupplyChainGraph,
} from "../types/sbom";
import { apiRequest } from "./client";

export async function ingestSbom(vendorId: string, content: string, documentName?: string): Promise<IngestResponse> {
  return apiRequest<IngestResponse>("/sbom/ingest", {
    method: "POST",
    body: { vendor_id: vendorId, content, document_name: documentName },
  });
}

export async function listVendorSboms(vendorId: string): Promise<SbomDocument[]> {
  return apiRequest<SbomDocument[]>(`/sbom/vendors/${vendorId}/documents`);
}

export async function listVendorComponents(vendorId: string, vulnerableOnly = false): Promise<SbomComponent[]> {
  const q = vulnerableOnly ? "?vulnerable_only=true" : "";
  return apiRequest<SbomComponent[]>(`/sbom/vendors/${vendorId}/components${q}`);
}

export async function listVendorVulnerabilities(vendorId: string): Promise<SbomVulnerability[]> {
  return apiRequest<SbomVulnerability[]>(`/sbom/vendors/${vendorId}/vulnerabilities`);
}

export async function getSupplyChainGraph(vendorId?: string): Promise<SupplyChainGraph> {
  const q = vendorId ? `?vendor_id=${vendorId}` : "";
  return apiRequest<SupplyChainGraph>(`/sbom/graph${q}`);
}

export async function getCriticalPathVendors(limit = 10): Promise<CriticalPathVendor[]> {
  return apiRequest<CriticalPathVendor[]>(`/sbom/graph/critical-path?limit=${limit}`);
}

export async function getCveImpact(cveId: string): Promise<SbomComponent[]> {
  return apiRequest<SbomComponent[]>(`/sbom/graph/cve/${encodeURIComponent(cveId)}/impact`);
}
