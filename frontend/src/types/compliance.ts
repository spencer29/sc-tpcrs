// Mirrors services/compliance-service/app/schemas.py.

export type ControlStatus = "met" | "partial" | "gap" | "not_applicable";
export type AssessmentStatus = "Compliant" | "Partially Compliant" | "Non-Compliant";

export interface Control {
  control_id: string;
  framework: string;
  reference: string;
  domain: string;
  title: string;
  objective: string;
  weight: number;
  tags: string[];
}

export interface FrameworkSummary {
  framework: string;
  control_count: number;
}

export interface ControlLibrary {
  total_controls: number;
  frameworks: FrameworkSummary[];
}

export interface ControlOverride {
  control_id: string;
  status: ControlStatus;
  evidence?: string;
  remediation?: string;
}

export interface AssessmentRequest {
  vendor_id: string;
  framework?: string;
  overrides?: ControlOverride[];
}

export interface ControlResult {
  control_id: string;
  framework: string;
  reference: string;
  domain: string;
  title: string;
  weight: number;
  status: ControlStatus;
  is_critical_gap: boolean;
  evidence: string;
  remediation: string;
}

export interface Assessment {
  id: string;
  vendor_id: string;
  framework: string;
  compliance_score: number;
  status: AssessmentStatus;
  total_controls: number;
  compliant_count: number;
  partial_count: number;
  gap_count: number;
  critical_gap_count: number;
  framework_scores: Record<string, number>;
  created_by: string;
  created_at: string;
}

export interface DomainGap {
  domain: string;
  framework: string;
  total: number;
  met: number;
  partial: number;
  gap: number;
  not_applicable: number;
  score: number;
}

export interface GapAnalysis {
  assessment_id: string;
  vendor_id: string;
  framework: string;
  compliance_score: number;
  status: AssessmentStatus;
  by_domain: DomainGap[];
  gaps: ControlResult[];
}

export interface RegulatoryReport {
  generated_at: string;
  vendor_id: string;
  framework: string;
  assessment: Assessment;
  framework_breakdown: DomainGap[];
  control_register: ControlResult[];
  prioritised_gaps: ControlResult[];
  attestation: string;
}

export interface AssessmentListItem {
  id: string;
  vendor_id: string;
  framework: string;
  compliance_score: number;
  status: AssessmentStatus;
  critical_gap_count: number;
  created_at: string;
}

export interface ComplianceDashboard {
  total_assessments: number;
  vendors_assessed: number;
  average_score: number;
  status_breakdown: Record<string, number>;
  framework_coverage: Record<string, number>;
  worst_vendors: AssessmentListItem[];
}
