import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { createVendor, type VendorCreateInput } from "../api/vendors";
import { ApiError } from "../api/client";

const TIER_OPTIONS = ["Critical", "High", "Medium", "Low"];

export function VendorOnboardingWizard() {
  const navigate = useNavigate();
  const [form, setForm] = useState<VendorCreateInput>({
    name: "",
    legal_entity_name: "",
    country: "NG",
    industry: "",
    contact_name: "",
    contact_email: "",
    data_access_scope: "Medium",
    service_criticality: "Medium",
    integration_depth: "Medium",
  });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  function update<K extends keyof VendorCreateInput>(key: K, value: VendorCreateInput[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const vendor = await createVendor(form);
      navigate(`/vendors/${vendor.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create vendor");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Add Vendor</h1>
        <p className="page-subtitle">Register a new third-party vendor and compute its initial risk tier.</p>
      </div>
      <form onSubmit={handleSubmit} className="card" style={{ maxWidth: 560 }}>
        <div className="form-row">
          <label htmlFor="name">Vendor name</label>
          <input id="name" required value={form.name} onChange={(e) => update("name", e.target.value)} style={{ width: "100%" }} />
        </div>
        <div className="grid-2">
          <div className="form-row">
            <label htmlFor="legal_entity_name">Legal entity name</label>
            <input
              id="legal_entity_name"
              value={form.legal_entity_name}
              onChange={(e) => update("legal_entity_name", e.target.value)}
              style={{ width: "100%" }}
            />
          </div>
          <div className="form-row">
            <label htmlFor="industry">Service category</label>
            <input
              id="industry"
              value={form.industry}
              onChange={(e) => update("industry", e.target.value)}
              placeholder="e.g. Payment_Gateway"
              style={{ width: "100%" }}
            />
          </div>
        </div>
        <div className="grid-2">
          <div className="form-row">
            <label htmlFor="contact_name">Contact name</label>
            <input
              id="contact_name"
              value={form.contact_name}
              onChange={(e) => update("contact_name", e.target.value)}
              style={{ width: "100%" }}
            />
          </div>
          <div className="form-row">
            <label htmlFor="contact_email">Contact email</label>
            <input
              id="contact_email"
              type="email"
              value={form.contact_email}
              onChange={(e) => update("contact_email", e.target.value)}
              style={{ width: "100%" }}
            />
          </div>
        </div>

        <h3 className="card-title" style={{ marginTop: 8 }}>
          Risk Tiering
        </h3>
        <p className="card-description">
          Overall tier is computed automatically as the maximum of the three dimensions below.
        </p>
        <div className="grid-3">
          <div className="form-row">
            <label htmlFor="data_access_scope">Data access scope</label>
            <select
              id="data_access_scope"
              value={form.data_access_scope}
              onChange={(e) => update("data_access_scope", e.target.value)}
              style={{ width: "100%" }}
            >
              {TIER_OPTIONS.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </div>
          <div className="form-row">
            <label htmlFor="service_criticality">Service criticality</label>
            <select
              id="service_criticality"
              value={form.service_criticality}
              onChange={(e) => update("service_criticality", e.target.value)}
              style={{ width: "100%" }}
            >
              {TIER_OPTIONS.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </div>
          <div className="form-row">
            <label htmlFor="integration_depth">Integration depth</label>
            <select
              id="integration_depth"
              value={form.integration_depth}
              onChange={(e) => update("integration_depth", e.target.value)}
              style={{ width: "100%" }}
            >
              {TIER_OPTIONS.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </div>
        </div>

        {error && <p className="error-text">{error}</p>}
        <button type="submit" className="btn" disabled={busy}>
          {busy ? "Creating..." : "Create Vendor"}
        </button>
      </form>
    </div>
  );
}
