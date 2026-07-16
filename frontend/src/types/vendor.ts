export type Tier = "Critical" | "High" | "Medium" | "Low";

export type LifecycleState =
  | "INITIATED"
  | "QUESTIONNAIRE_SENT"
  | "QUESTIONNAIRE_COMPLETED"
  | "ASSESSMENT_IN_PROGRESS"
  | "ONBOARDED"
  | "REJECTED";

export interface Vendor {
  id: string;
  name: string;
  legal_entity_name: string | null;
  country: string | null;
  industry: string | null;
  contact_name: string | null;
  contact_email: string | null;
  data_access_scope: Tier;
  service_criticality: Tier;
  integration_depth: Tier;
  overall_tier: Tier;
  onboarding_state: LifecycleState;
  contract_start_date: string | null;
  contract_end_date: string | null;
  created_at: string;
  updated_at: string;
}

export interface VendorListResponse {
  items: Vendor[];
  page: number;
  size: number;
  total: number;
}

export type Answer = "YES" | "NO" | "PARTIAL" | "NA";

export interface Question {
  code: string;
  domain: string;
  text: string;
  answer: Answer | null;
  score: number | null;
}

export interface Questionnaire {
  id: string;
  vendor_id: string;
  tier: Tier;
  status: "SENT" | "IN_PROGRESS" | "COMPLETED";
  sent_at: string | null;
  completed_at: string | null;
  questions: Question[];
}

export interface VendorDocument {
  id: string;
  document_type: string;
  file_name: string;
  content_type: string | null;
  size_bytes: number | null;
  uploaded_at: string;
}
