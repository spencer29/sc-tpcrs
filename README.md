# SC-TPCRS — Supply Chain and Third-Party Cybersecurity Risk System

A microservices-based platform for fintech/payment organisations to onboard,
risk-tier, assess, and continuously monitor third-party vendors.

## What's built in this pass

This is an **iterative build** on top of the original blueprint spec. Each
pass adds one or more modules end-to-end (backend + tests + frontend slice)
in the blueprint's mandated order (1→2→3→5→4→6). Every design decision and
scope trade-off is documented inline in code, in [SECURITY.md](SECURITY.md),
and — for Module 3 — in the [Module 3 notes](#module-3--sbom--supply-chain-graph-notes)
below. Read those before assuming a "full" feature is present.

| Module | Service | Status |
|---|---|---|
| Auth (lite Keycloak substitute) | `auth-service` | Full — login, MFA (TOTP), JWT issuance |
| API Gateway (lite Kong substitute) | `gateway` | Full — JWT validation, rate limiting, routing |
| 1. Vendor Lifecycle Management | `vendor-service` | Full |
| 2. Automated Risk Assessment Engine | `risk-service` | Full, including anomaly detection |
| 3. Supply Chain Visibility / SBOM | `sbom-service` | Full — CycloneDX/SPDX ingestion, CVE cross-ref, dependency graph |
| 4. Continuous Monitoring | `monitoring-service` | Health-only skeleton (deferred) |
| 5. Compliance Monitoring | `compliance-service` | Health-only skeleton (deferred) |
| 6. Incident Response Integration | `incident-service` | Health-only skeleton (deferred) |
| Frontend | `frontend` (React + TS + Vite) | Login, Vendor List/Detail/Onboarding, Risk Dashboard |

Scoped-down numbers relative to the original spec (all documented in-code,
not oversights): a 36-question security questionnaire bank (not 240), 20
seeded demo vendors (not 50), an ~800-sample synthetic anomaly-detection
training set (not 10,000).

## Architecture

```
React SPA (Vite, :5173)
        |
        v
   gateway (:8080)  -- JWT validation, rate limiting, routing --
        |
   +----+----+----+----+----+----+----+
   |    |    |    |    |    |    |    |
 auth vendor risk sbom compl monit incid
 :8001 :8002 :8003 :8004 :8005 :8006 :8007
   |    |    |
   +----+----+---> Postgres (:5432, one DB per service)
        |
        +---> Kafka (:9092) -- vendor.lifecycle.events, risk.score.updates, ...
        +---> Redis (:6379) -- caching, rate limiting
        +---> Neo4j (:7474/:7687) -- vendor→component→CVE dependency graph (sbom-service writes)
```

Every service talks to the outside world only through the shared library
`shared/py-common` (`sc_tpcrs_common`): stateless HS256 JWT validation
(`jwt_shared.py`), mock/real external adapters (`adapters/`), fail-soft
Kafka/Redis wrappers, and a hash-chained audit log.

## Prerequisites

Only **Docker Desktop**. Node/npm and a Python interpreter are not required
on the host — everything (including the frontend's `npm install`) runs
inside containers.

## Quickstart

```bash
cp .env.example .env         # adjust if needed; safe defaults for local dev
docker compose up -d postgres neo4j redis kafka
# wait for them to report healthy: docker compose ps
docker compose up -d --build
docker compose --profile tools run --rm seed
```

Then open:
- Frontend: http://localhost:5173
- Gateway (API root): http://localhost:8080
- Each service's own Swagger UI (bypassing the gateway, for debugging):
  `http://localhost:800{1..7}/docs`
- Neo4j Browser: http://localhost:7474
- Kibana/Grafana are not wired up this pass (structured JSON logs only, per service stdout)

Demo login credentials (all 8 seeded users share one password): see
[seed/README.md](seed/README.md), generated after running the seed step
above. MFA codes can be fetched via `GET /api/auth/dev/mfa-code?email=...`
(dev-only endpoint, disabled outside `ENV=development`) instead of a real
authenticator app.

## Makefile targets

```
make up      # docker compose up -d --build
make down    # docker compose down
make logs    # docker compose logs -f
make seed    # run the one-shot seed service
make train-anomaly-model   # retrain risk-service's XGBoost anomaly model
make test-<service>        # run one service's pytest suite in a container
```

## Testing

Each fully-built service (`auth-service`, `gateway`, `vendor-service`,
`risk-service`, `sbom-service`) has its own pytest suite covering core
business logic: tiering boundaries, state-machine transitions, the VRS
weighted formula, JWT issuance/expiry/role checks, rate-limit thresholds, and
(for `sbom-service`) SBOM parsing, PURL normalisation, the SSRF guard, CVE/SSVC
scanning, and the full ingest API including Demo Scenario 1. This pass
targets realistic coverage of that business logic (roughly 60-70%), **not**
a repo-wide 80% target — DB-heavy integration paths and the frontend are
verified manually per the walkthrough in `SECURITY.md`'s companion plan
rather than with exhaustive automated tests this pass.

Run a single service's tests locally (from a Python virtualenv with
`shared/py-common` and that service installed):
```bash
python -m pytest services/<name>/tests -q
```

## Repository layout

```
shared/py-common/     sc_tpcrs_common: JWT, Kafka, Redis, audit log, adapters
infrastructure/       Dockerfile pattern, Postgres/Neo4j init scripts
services/             one directory per microservice (see table above)
frontend/             React + TypeScript + Vite SPA
seed/                 one-shot seed script + generated credentials README
```

## Module 3 — SBOM / Supply-Chain Graph notes

`sbom-service` ingests Software Bills of Materials, cross-references components
against known CVEs, and builds a vendor→component→vulnerability dependency
graph. Key endpoints (all behind the gateway at `/api/sbom/...`):

- `POST /sbom/ingest` — accepts **CycloneDX** (JSON or XML, spec ≥ 1.4) and
  **SPDX** (JSON or tag-value). Format/serialization are auto-detected. Returns
  the stored document, its components, and a `critical_vulnerabilities`
  roll-up. Role-gated to `risk_officer` / `ciso` / `admin`.
- `GET /sbom/vendors/{id}/documents|components|vulnerabilities` — per-vendor
  views (`components?vulnerable_only=true` filters to components with findings).
- `GET /sbom/graph` — force-directed supply-chain graph (optional `vendor_id`
  scope); `GET /sbom/graph/critical-path` — vendors ranked by centrality;
  `GET /sbom/graph/cve/{cve_id}/impact` — every affected component across the
  portfolio (blast-radius query).

**Demo Scenario 1** is wired end-to-end: ingesting an SBOM containing
`left-pad@1.0.0` (npm) deterministically surfaces the planted, KEV-listed
`CVE-2024-99999` (CVSS 9.8) with SSVC priority **Act**, and the CVE-impact
endpoint returns the affected component in seconds. The frontend
**Supply Chain** page drives this with a one-click sample SBOM.

### Documented deviations (faithful equivalents)

Per the blueprint's "closest faithful equivalent behind an interface, document
the deviation" guidance:

- **GDS analytics → networkx.** Neo4j Community Edition lacks the Graph Data
  Science plugin, so betweenness centrality / PageRank (the blueprint's
  critical-path asks) are computed with `networkx` over the subgraph fetched
  from Neo4j. Comfortably meets the < 3s target at the 1,000-node scale. The
  read path (`services/graph.py`) is the single interface, so swapping in real
  GDS later is a localised change.
- **Neo4j graph is a fail-soft enhancement.** The relational store (Postgres)
  is authoritative for components and vulnerabilities; the graph mirror and
  Kafka events are best-effort and never fail an ingest. If Neo4j is down,
  ingestion still succeeds and graph reads degrade to an empty graph rather
  than erroring. `NEO4J_ENABLED=false` disables the mirror entirely (used in
  unit tests).
- **Mock NVD / CISA KEV adapters.** CVE data comes from the shared mock
  adapters (`sc_tpcrs_common.adapters`, same as risk-service), deterministic
  and offline by default. They share the `ExternalAdapter` interface with the
  real-mode implementations, so setting the adapter mode to `real` (with an
  `NVD_API_KEY`) switches to live lookups without touching `sbom-service`.
- **SSVC decision tree — simplified.** A faithful subset of CISA's deployer
  tree (Act / Attend / Track* / Track); "automatable" is approximated by a
  network attack vector with low complexity (`AV:N/AC:L`), "high impact" by
  CVSS ≥ 7.0. Documented in `services/cve_scanner.py`.
- **SSRF-guarded external references.** SBOM URL/reference fields are never
  fetched by default (`sbom_fetch_external_refs=false`); when enabled, an
  allow-list plus private/loopback/link-local IP rejection (fail-closed on
  unresolvable hosts) governs any outbound fetch. See `services/ssrf_guard.py`.

## Further reading

- [SECURITY.md](SECURITY.md) — auth posture, encryption, audit log guarantees,
  mock-vs-real adapter posture, and explicit scope trade-offs for this pass.
