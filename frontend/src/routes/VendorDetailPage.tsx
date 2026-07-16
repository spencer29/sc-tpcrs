import { useCallback, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import {
  generateQuestionnaire,
  getQuestionnaire,
  getVendor,
  listDocuments,
  submitQuestionnaireResponses,
  transitionVendor,
} from "../api/vendors";
import { computeRiskScore, getLatestRiskScore } from "../api/risk";
import { ApiError } from "../api/client";
import { VendorTierBadge } from "../components/VendorTierBadge";
import { VrsGauge } from "../components/VrsGauge";
import { RoleGate } from "../auth/RoleGate";
import type { Answer, Questionnaire, Vendor, VendorDocument } from "../types/vendor";
import type { RiskScore } from "../types/risk";

const NEXT_STATE: Partial<Record<Vendor["onboarding_state"], Vendor["onboarding_state"]>> = {
  QUESTIONNAIRE_COMPLETED: "ASSESSMENT_IN_PROGRESS",
};

const ANSWER_OPTIONS: Answer[] = ["YES", "PARTIAL", "NO", "NA"];

export function VendorDetailPage() {
  const { vendorId } = useParams<{ vendorId: string }>();
  const [vendor, setVendor] = useState<Vendor | null>(null);
  const [questionnaire, setQuestionnaire] = useState<Questionnaire | null>(null);
  const [documents, setDocuments] = useState<VendorDocument[]>([]);
  const [riskScore, setRiskScore] = useState<RiskScore | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [draftAnswers, setDraftAnswers] = useState<Record<string, Answer>>({});

  const reload = useCallback(async () => {
    if (!vendorId) return;
    const v = await getVendor(vendorId);
    setVendor(v);
    try {
      setQuestionnaire(await getQuestionnaire(vendorId));
    } catch {
      setQuestionnaire(null);
    }
    try {
      setDocuments(await listDocuments(vendorId));
    } catch {
      setDocuments([]);
    }
    try {
      setRiskScore(await getLatestRiskScore(vendorId));
    } catch {
      setRiskScore(null);
    }
  }, [vendorId]);

  useEffect(() => {
    reload().catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load vendor"));
  }, [reload]);

  if (!vendor) {
    return error ? <p className="error-text">{error}</p> : <p>Loading...</p>;
  }

  async function withBusy(action: () => Promise<void>) {
    setBusy(true);
    setError(null);
    try {
      await action();
      await reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Action failed");
    } finally {
      setBusy(false);
    }
  }

  const nextState = NEXT_STATE[vendor.onboarding_state];

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title" style={{ marginBottom: 8 }}>
          {vendor.name}
        </h1>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <VendorTierBadge tier={vendor.overall_tier} />
          <span style={{ color: "hsl(var(--muted-foreground))", fontSize: "0.85rem" }}>
            {vendor.onboarding_state.replaceAll("_", " ")}
          </span>
        </div>
      </div>

      {error && <p className="error-text">{error}</p>}

      <div className="grid-2" style={{ marginTop: 16 }}>
        <div className="card">
          <h3 className="card-title">Overview</h3>
          <p>
            <strong>Legal entity:</strong> {vendor.legal_entity_name ?? "—"}
            <br />
            <strong>Industry:</strong> {vendor.industry ?? "—"}
            <br />
            <strong>Country:</strong> {vendor.country ?? "—"}
            <br />
            <strong>Contact:</strong> {vendor.contact_name ?? "—"} ({vendor.contact_email ?? "—"})
          </p>
          <h4>Tier dimensions</h4>
          <p>
            Data access scope: <VendorTierBadge tier={vendor.data_access_scope} />
            <br />
            <br />
            Service criticality: <VendorTierBadge tier={vendor.service_criticality} />
            <br />
            <br />
            Integration depth: <VendorTierBadge tier={vendor.integration_depth} />
          </p>

          <RoleGate allow={["risk_officer", "ciso", "admin"]}>
            <div style={{ marginTop: 12, display: "flex", gap: 8 }}>
              {vendor.onboarding_state === "INITIATED" && (
                <button
                  className="btn"
                  disabled={busy}
                  onClick={() =>
                    withBusy(async () => {
                      await generateQuestionnaire(vendor.id);
                    })
                  }
                >
                  Send Questionnaire
                </button>
              )}
              {nextState && (
                <button
                  className="btn"
                  disabled={busy}
                  onClick={() => withBusy(async () => void (await transitionVendor(vendor.id, nextState)))}
                >
                  Advance to {nextState.replaceAll("_", " ")}
                </button>
              )}
              {vendor.onboarding_state === "ASSESSMENT_IN_PROGRESS" && (
                <>
                  <button
                    className="btn"
                    disabled={busy}
                    onClick={() => withBusy(async () => void (await transitionVendor(vendor.id, "ONBOARDED")))}
                  >
                    Approve (Onboard)
                  </button>
                  <button
                    className="btn btn-secondary"
                    disabled={busy}
                    onClick={() => withBusy(async () => void (await transitionVendor(vendor.id, "REJECTED")))}
                  >
                    Reject
                  </button>
                </>
              )}
            </div>
          </RoleGate>
        </div>

        <div className="card">
          <h3 className="card-title">Risk Score</h3>
          {riskScore ? (
            <>
              <VrsGauge score={riskScore.vrs_score} tier={riskScore.tier} />
              <table style={{ marginTop: 16 }}>
                <tbody>
                  <tr>
                    <td>Questionnaire</td>
                    <td>{riskScore.questionnaire_score.toFixed(1)}</td>
                  </tr>
                  <tr>
                    <td>External posture</td>
                    <td>{riskScore.external_posture_score.toFixed(1)}</td>
                  </tr>
                  <tr>
                    <td>Vulnerability exposure</td>
                    <td>{riskScore.vulnerability_score.toFixed(1)}</td>
                  </tr>
                  <tr>
                    <td>Breach history</td>
                    <td>{riskScore.breach_history_score.toFixed(1)}</td>
                  </tr>
                  <tr>
                    <td>Threat intelligence</td>
                    <td>{riskScore.threat_intel_score.toFixed(1)}</td>
                  </tr>
                  <tr>
                    <td>Compliance</td>
                    <td>{riskScore.compliance_score.toFixed(1)}</td>
                  </tr>
                </tbody>
              </table>
            </>
          ) : (
            <p style={{ color: "hsl(var(--muted-foreground))" }}>No risk score computed yet.</p>
          )}
          <RoleGate allow={["risk_officer", "ciso", "admin"]}>
            <button
              className="btn"
              style={{ marginTop: 12 }}
              disabled={busy}
              onClick={() => withBusy(async () => void (await computeRiskScore(vendor.id)))}
            >
              Recompute
            </button>
          </RoleGate>
        </div>
      </div>

      <div className="card" style={{ marginTop: 16 }}>
        <h3 className="card-title">
          Questionnaire {questionnaire && `(${questionnaire.status.replaceAll("_", " ")})`}
        </h3>
        {!questionnaire && <p style={{ color: "hsl(var(--muted-foreground))" }}>No questionnaire generated yet.</p>}
        {questionnaire && questionnaire.status !== "COMPLETED" && (
          <RoleGate allow={["risk_officer", "compliance_manager", "ciso", "admin"]}>
            <div>
              {questionnaire.questions.map((q) => (
                <div key={q.code} style={{ marginBottom: 10 }}>
                  <div style={{ fontSize: "0.85rem", color: "hsl(var(--muted-foreground))" }}>
                    {q.domain} &middot; {q.code}
                  </div>
                  <div style={{ marginBottom: 4 }}>{q.text}</div>
                  <select
                    value={draftAnswers[q.code] ?? q.answer ?? ""}
                    onChange={(e) =>
                      setDraftAnswers((prev) => ({ ...prev, [q.code]: e.target.value as Answer }))
                    }
                  >
                    <option value="" disabled>
                      Select answer
                    </option>
                    {ANSWER_OPTIONS.map((a) => (
                      <option key={a} value={a}>
                        {a}
                      </option>
                    ))}
                  </select>
                </div>
              ))}
              <button
                className="btn"
                disabled={busy}
                onClick={() =>
                  withBusy(async () => {
                    const responses = Object.entries(draftAnswers).map(([question_code, answer]) => ({
                      question_code,
                      answer,
                    }));
                    if (responses.length === 0) return;
                    await submitQuestionnaireResponses(vendor.id, responses);
                    setDraftAnswers({});
                  })
                }
              >
                Submit Answers
              </button>
            </div>
          </RoleGate>
        )}
        {questionnaire && questionnaire.status === "COMPLETED" && (
          <p style={{ color: "hsl(var(--muted-foreground))" }}>
            All {questionnaire.questions.length} questions answered.
          </p>
        )}
      </div>

      <div className="card" style={{ marginTop: 16 }}>
        <h3 className="card-title">Documents</h3>
        {documents.length === 0 ? (
          <p style={{ color: "hsl(var(--muted-foreground))" }}>No documents uploaded.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Type</th>
                <th>File</th>
                <th>Uploaded</th>
              </tr>
            </thead>
            <tbody>
              {documents.map((doc) => (
                <tr key={doc.id}>
                  <td>{doc.document_type}</td>
                  <td>{doc.file_name}</td>
                  <td>{new Date(doc.uploaded_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
