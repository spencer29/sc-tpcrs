export interface SbomVulnerability {
  id: string;
  cve_id: string;
  description: string | null;
  cvss_score: number | null;
  severity: "Critical" | "High" | "Medium" | "Low" | "None";
  kev_flag: boolean;
  known_ransomware: boolean;
  ssvc_priority: "Act" | "Attend" | "Track*" | "Track";
  status: string;
}

export interface SbomComponent {
  id: string;
  vendor_id: string;
  component_name: string;
  version: string;
  ecosystem: string;
  purl: string;
  cpe: string | null;
  purl_synthesised: boolean;
  vulnerabilities: SbomVulnerability[];
}

export interface SbomDocument {
  id: string;
  vendor_id: string;
  sbom_format: string;
  spec_version: string | null;
  serialization: string | null;
  document_name: string | null;
  component_count: number;
  vulnerable_count: number;
  incomplete: boolean;
  review_notes: Record<string, unknown>;
  ingested_at: string;
}

export interface IngestResponse {
  document: SbomDocument;
  components: SbomComponent[];
  critical_vulnerabilities: SbomVulnerability[];
  processing_ms: number;
}

export interface GraphNode {
  id: string;
  label: "Vendor" | "SoftwareComponent" | "Vulnerability";
  name: string;
  tier: string | null;
  severity: string | null;
  critical_path: boolean;
  centrality: number | null;
}

export interface GraphEdge {
  source: string;
  target: string;
  type: "PROVIDES" | "DEPENDS_ON" | "AT_RISK";
}

export interface SupplyChainGraph {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface CriticalPathVendor {
  vendor_id: string;
  name: string;
  betweenness: number;
  pagerank: number;
  dependent_component_count: number;
}
