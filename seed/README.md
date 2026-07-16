# Seed data

Run via `make seed` or `docker compose --profile tools run --rm seed`
(requires `gateway`, `auth-service`, `vendor-service`, and `risk-service`
already up and healthy). Idempotent for users (re-running skips existing
demo accounts); re-running the whole script will create a **second** batch
of vendors, since vendor creation has no idempotency key in this pass.

## What gets seeded

- **8 demo users** (2 per role: `risk_officer`, `compliance_manager`,
  `ciso`, `admin`) via auth-service's dev-only `/auth/dev/seed-users`
  endpoint. All 8 share one password: **`Demo1234!`**. Fetch a login MFA
  code for any of them via
  `GET /api/auth/dev/mfa-code?email=<email>` (dev-only, see SECURITY.md).

  | Email | Role |
  |---|---|
  | risk.officer1@sc-tpcrs.demo | risk_officer |
  | risk.officer2@sc-tpcrs.demo | risk_officer |
  | compliance1@sc-tpcrs.demo | compliance_manager |
  | compliance2@sc-tpcrs.demo | compliance_manager |
  | ciso1@sc-tpcrs.demo | ciso |
  | ciso2@sc-tpcrs.demo | ciso |
  | admin1@sc-tpcrs.demo | admin |
  | admin2@sc-tpcrs.demo | admin |

- **20 vendors** (19 fictional-name templates in `vendor_templates.py` + 1
  hardcoded demo vendor), each advanced through the **real** onboarding API
  workflow (questionnaire generation, answering, lifecycle transitions --
  not a database shortcut), distributed across all 6 onboarding states.
- **1 demo vendor** ("Demo Critical Vendor (left-pad)"), forced to Critical
  tier, questionnaire answered 100% YES, **no** compliance documents
  uploaded, and its tech stack seeded with exactly `left-pad@1.0.0` (npm) --
  which `shared/py-common/sc_tpcrs_common/adapters/planted.py` guarantees
  resolves to a CVSS 9.8, KEV-listed CVE. This makes its
  `vulnerability_score` a **known constant: 40.0** (100 minus the 60-point
  critical+KEV penalty -- see `services/risk-service/app/services/
  category_sources/vulnerability_source.py`) regardless of seed run, and its
  `questionnaire_score` a known constant: **100.0**, and its
  `compliance_score` a known constant: **0.0**. Its `external_posture_score`
  / `breach_history_score` / `threat_intel_score` are deterministic *per
  vendor UUID* (mock adapters are seeded by vendor_id) but the UUID itself
  is server-generated, so those three values aren't knowable ahead of a
  given run -- see the generated `SEED_RESULTS.md` (below) for the actual
  numbers from your run.
- **Tech stack stubs** for every vendor (2-5 mock components each, standing
  in for real SBOM ingestion -- `sbom-service` is deferred).
- **Initial risk scores** computed for every vendor at
  `QUESTIONNAIRE_COMPLETED` or later.

## SEED_RESULTS.md

After seeding, `seed/SEED_RESULTS.md` is generated (gitignored -- it's
per-run output, not source) documenting the actual vendor UUIDs and
computed VRS/category breakdowns from that run, including the demo
vendor's full breakdown. Use it as the concrete input to the manual
verification walkthrough in the root `README.md`.

## Scope note

`SEED_VENDOR_COUNT`/`SEED_RANDOM_SEED` env vars are read by `config.py` but
`vendor_templates.py` currently only defines 19 named templates + 1 demo
vendor (20 total) -- raising `SEED_VENDOR_COUNT` beyond 20 will reuse
templates via index wraparound rather than generating new ones. Extending
`vendor_templates.py` with more fictional entries is the straightforward
way to seed a larger demo dataset later.
