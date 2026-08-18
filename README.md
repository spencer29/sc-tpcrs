# SC-TPCRS — Supply Chain and Third-Party Cybersecurity Risk System

A microservices-based platform for fintech/payment organisations to onboard,
risk-tier, assess, and continuously monitor third-party vendors.

## What's built in this pass

This is an **iterative build** on top of the original blueprint spec. Each
pass adds one or more modules end-to-end (backend + tests + frontend slice)
in the blueprint's mandated order (1→2→3→5→4→6). Every design decision and
scope trade-off is documented inline in code, in [SECURITY.md](SECURITY.md),
and — for Modules 3, 4, 5 and 6 — in the [Module 3 notes](#module-3--sbom--supply-chain-graph-notes),
[Module 4 notes](#module-4--continuous-monitoring-notes), [Module 5 notes](#module-5--compliance-monitoring-notes)
and [Module 6 notes](#module-6--incident-response-integration-notes)
below. Read those before assuming a "full" feature is present.

| Module | Service | Status |
|---|---|---|
| Auth (lite Keycloak substitute) | `auth-service` | Full — login, MFA (TOTP), JWT issuance |
| API Gateway (lite Kong substitute) | `gateway` | Full — JWT validation, rate limiting, routing |
| 1. Vendor Lifecycle Management | `vendor-service` | Full |
| 2. Automated Risk Assessment Engine | `risk-service` | Full, including anomaly detection |
| 3. Supply Chain Visibility / SBOM | `sbom-service` | Full — CycloneDX/SPDX ingestion, CVE cross-ref, dependency graph |
| 4. Continuous Monitoring | `monitoring-service` | Full — periodic posture sweeps, drift/exposure/threat-intel alerting, cross-module event reactions |
| 5. Compliance Monitoring | `compliance-service` | Full — 281-control library, gap analysis, regulator-ready reports |
| 6. Incident Response Integration | `incident-service` | Full — auto-opens incidents from monitoring alerts, lifecycle/SLA tracking, CBN/NDPC regulatory notification drafting |
| Frontend | `frontend` (React + TS + Vite) | Login, Vendor List/Detail/Onboarding, Risk Dashboard, Supply Chain, Compliance, Monitoring/Alerts, Incidents |

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

## Production deployment

The Quickstart above is the dev stack (all ports exposed, hot-reload Vite,
single-worker services). Two hardened paths exist for going further:

- **Single-host Docker** — apply the [docker-compose.prod.yml](docker-compose.prod.yml)
  overlay on top of the base file: closes every host port except the gateway
  (`:8080`) and the nginx-served SPA (`:8081`), adds `restart: unless-stopped`,
  runs multi-worker uvicorn, and swaps the Vite dev server for a static nginx
  build. Neo4j and Kafka stay in-cluster, so the graph and event choreography
  are fully live. See **[PROD_DOCKER.md](PROD_DOCKER.md)**.
- **Managed cloud (Render)** — web services + managed Postgres, per the
  [render.yaml](render.yaml) blueprint. See **[RENDER_DEPLOY.md](RENDER_DEPLOY.md)**.

## Testing

Each fully-built service (`auth-service`, `gateway`, `vendor-service`,
`risk-service`, `sbom-service`, `compliance-service`, `monitoring-service`,
`incident-service`) has
its own pytest suite covering core business logic: tiering boundaries,
state-machine transitions, the VRS weighted formula, JWT issuance/expiry/role
checks, rate-limit thresholds, (for `sbom-service`) SBOM parsing, PURL
normalisation, the SSRF guard, CVE/SSVC scanning, and the full ingest API
including Demo Scenario 1, (for `compliance-service`) the control library
integrity, weighted scoring / gap ranking, deterministic per-vendor evidence,
override precedence, and the full assessment → gap-analysis → report API flow
(26 tests), and (for `monitoring-service`) the exposure-index math, deterministic
posture collection, drift/alert-engine thresholds, alert dedup/escalation,
Kafka-event→alert mapping, the full sweep flow, and the alert acknowledge/resolve
API (45 tests), and (for `incident-service`) the lifecycle state machine and
SLA/severity gating, CBN/NDPC notification drafting, incident create/transition/
dedup logic, monitoring-alert→incident auto-open, and the full incident REST API
including RBAC, illegal-transition 409s, and the response dashboard (48 tests). This pass
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

## Module 4 — Continuous Monitoring notes

`monitoring-service` is the continuous-monitoring hub: it periodically sweeps every
vendor's external security posture, records an append-only snapshot time series,
raises deduplicated alerts on posture drift / newly-exposed services / threat-intel
matches, and also reacts to alert-worthy events published by the other modules. It
publishes its own alerts to the `monitoring.alerts` Kafka topic for
`incident-service` (Module 6) to consume. Key endpoints (all behind the gateway at
`/api/monitoring/...`):

- `GET /monitoring/dashboard` — portfolio posture roll-up: vendors monitored, open
  alerts by severity and type, average exposure index, and the highest-exposure
  vendors. Aggregates over this service's own rows only (same convention as the
  risk/compliance dashboards — no cross-service HTTP fan-out).
- `POST /monitoring/sweep` — trigger a portfolio sweep on demand (202 Accepted).
  Role-gated to `risk_officer` / `ciso` / `admin`. The in-process scheduler runs the
  same sweep automatically every `sweep_interval_seconds` (default 900s) plus once
  shortly after startup, so a running stack always has fresh data.
- `GET /monitoring/snapshots` — latest snapshot per vendor, worst exposure first;
  `GET /monitoring/vendors/{vendor_id}/snapshots` — a vendor's snapshot history.
- `GET /monitoring/alerts` (filter by `vendor_id` / `status` / `severity`),
  `GET /monitoring/alerts/{id}`, and `POST /monitoring/alerts/{id}/acknowledge` /
  `POST /monitoring/alerts/{id}/resolve` (writer-gated) — the alert triage lifecycle.
  Every acknowledge/resolve is written to the hash-chained `audit_log`.

**Posture signals & exposure index.** Each sweep folds three of the shared mock
adapters — Shodan (posture score + open services), MISP (threat-intel IOC matches),
and AbuseIPDB (abuse reports) — into a single 0-100 **exposure index** (higher =
worse; weights 0.6 posture / 0.25 IOC / 0.15 abuse, counts capped). These are the
same deterministic SHA256-seeded adapters `risk-service` uses, so a vendor's posture
is stable across sweeps *until its inputs change* — which is exactly what makes drift
meaningful. **Deviation from spec:** real continuous monitoring would poll live
Shodan/MISP/AbuseIPDB APIs on a schedule; here the adapters are deterministic mocks
(set `{ADAPTER}_MODE=live` to swap in a real implementation behind the same
interface). To make drift demoable without waiting for real-world change, a sweep
applies a deterministic per-(vendor, epoch) "drift probe" (`posture.rotating_probe`):
~70% of sweeps read the vendor's stable baseline, the rest read a perturbed-but-still-
deterministic posture, so a long-running stack naturally produces the occasional drift
alert — and the manual `POST /monitoring/sweep` uses a separate epoch space so drift
can be surfaced on demand.

**Alerting.** `alert_engine.evaluate_snapshot` turns a fresh snapshot into alert specs
(drift crossing the warning ≥8 / critical ≥20 thresholds; newly-exposed sensitive
services rdp/ftp/smtp/telnet; active IOC matches). `alert_engine.alert_from_event`
maps an inbound Kafka event to an alert. Both feed `upsert_alert`, which **deduplicates
on (vendor_id, dedup_key) among non-resolved alerts** — a repeat of the same open
finding bumps `occurrence_count`/`last_seen_at` and escalates severity rather than
spamming a new row every sweep; a resolved finding that recurs opens a fresh alert.

**Event flow.** monitoring-service *consumes* `cve.alerts` (sbom-service),
`compliance.assessment.events` (compliance-service), and `risk.anomaly.alerts`
(risk-service), and *publishes* `monitoring.alerts`. The shared Kafka consumer
dispatches every topic to one handler, so `events.handle_event` recovers the
originating topic from the event's `event_type` prefix. All Kafka is fail-soft (the
shared producer/consumer no-op when no broker is reachable), so unit tests and offline
demos need no Kafka.

**Deviation from spec — scheduler.** A production deployment would drive sweeps from
Celery-beat or a cron sidecar; to keep the prototype self-contained (no extra broker
process) the periodic sweep runs on an asyncio background task started in the FastAPI
lifespan, mirroring the Kafka consumer's lifecycle. The manual endpoint and the
scheduler share the same underlying `run_sweep`.

## Module 5 — Compliance Monitoring notes

`compliance-service` delivers automated compliance gap analysis and regulator-ready
reporting against a multi-framework control library. Key endpoints (all behind the
gateway at `/api/compliance/...`):

- `GET /compliance/controls` — library summary (281 controls across 5 frameworks);
  `GET /compliance/controls/list?framework=<name>` — per-framework control catalogue.
- `POST /compliance/assessments` — run a full-library (`framework=ALL`) or
  single-framework assessment against a vendor. Returns the scored assessment with
  compliance_score (weighted 0-100), status (Compliant ≥85%, Partially Compliant
  ≥60%, Non-Compliant <60%), and per-control results. Role-gated to
  `compliance_manager` / `ciso` / `admin`. Optional manual overrides allow evidence
  reviews to supersede the baseline.
- `GET /compliance/assessments/{id}/gap-analysis` — domain-breakdown (worst-scoring
  domains first) + prioritised gaps (critical gaps first, then by control weight).
- `GET /compliance/assessments/{id}/report` — regulator-ready report with attestation
  narrative, full control register, and prioritised remediation list.
- `GET /compliance/dashboard` — portfolio-wide posture (average score, status
  breakdown, framework coverage, worst performers).

**Demo value**: Running a full-library assessment against any vendor deterministically
yields a meaningful compliance spread (typically 60-85%, with 3-8 critical gaps) in
under 2 seconds. The gap-analysis and report endpoints provide the narrative and
structure regulators expect.

### Control library (281 controls, 5 frameworks)

The blueprint specified ~312 controls; the faithful equivalent implemented here is
**281 authentic controls** drawn from the real published standards:

- **ISO/IEC 27001:2022** — all 93 Annex A controls (A.5 Organizational, A.6 People,
  A.7 Physical, A.8 Technological), with real reference IDs (e.g. `5.19 — Information
  security in supplier relationships`).
- **PCI DSS v4.0** — 77 controls spanning all 12 requirements (Build and Maintain
  a Secure Network, Protect Account Data, Maintain a Vulnerability Management
  Program, ...). Real sub-requirement IDs like `8.4.2 — MFA for access into the CDE`.
- **SOC 2 (2017 TSC)** — 52 controls across Common Criteria (CC1-CC9) + category-specific
  criteria (Availability, Confidentiality, Processing Integrity, Privacy).
- **NDPR 2019 / NDPA 2023** — 30 controls covering Nigeria's data protection regime
  (consent, lawful basis, cross-border transfers, breach notification, DPO appointment).
- **CBN Risk-Based Cybersecurity Framework** — 29 controls from the Central Bank of
  Nigeria's framework for financial institutions (governance, access control, incident
  response, business continuity).

Every control carries a **weight** (1-5, material controls weighted 4-5) that governs
the compliance score calculation and critical-gap flagging. A control at weight 5
that shows a gap is automatically flagged critical and ranked first in remediation
lists. Third-party / supplier controls are explicitly tagged (e.g. ISO 27001's A.5.19,
PCI-DSS supply-chain requirements) to support Module 5's vendor-context mission.

### Assessment engine — deterministic mock evidence

Per the blueprint's "closest faithful equivalent" guidance, the assessment engine
produces **deterministic mock evidence** rather than integrating live compliance
tooling. Each (vendor_id, control_id) pair is hashed (SHA256) to seed a pseudo-random
evaluation that yields one of four statuses:

- **met** (≈60% base rate, reduced for high-weight controls)
- **partial** (≈22%)
- **gap** (≈13%, increased for high-weight controls — weight-5 controls gap ≈20% of the time)
- **not_applicable** (≈5%)

The bias ensures every vendor reproducibly shows a meaningful compliance spread with
several critical gaps (weight ≥4 + status=gap), making the gap-analysis and reporting
endpoints immediately useful in demos. The seeded approach also means re-running the
same assessment yields identical results (a test requirement and audit expectation).

Manual overrides are supported: a compliance manager can mark a control as `met` with
auditor-reviewed evidence, which takes precedence over the baseline and raises the
score. This models the real-world review cycle.

The deterministic mock is the **documented deviation** from live evidence collection
(which would require integrations to SIEM, IAM, ticketing, policy repos, and audit
trail sources). The interface is `assessment_engine.evaluate_controls(vendor_id,
framework, overrides)`, so swapping in real adapters is a localised change when those
integrations are built.

### Event-driven assessment

`compliance-service` subscribes to `vendor.lifecycle.events` (Kafka). When a vendor
reaches `ONBOARDED` or `ASSESSMENT_IN_PROGRESS` state, the service automatically runs
a full-library compliance assessment and publishes the result to
`compliance.assessment.events`. This mirrors the risk-service's event-driven VRS
scoring and keeps the compliance posture current as vendors move through onboarding.

The Kafka consumer is best-effort (fail-soft) — if the broker is down or the
assessment fails, the event is logged but the consumer stays healthy and ingestion
continues. Manual assessments via `POST /compliance/assessments` remain available
regardless of Kafka state.

### Frameworks covered

The five frameworks were chosen for the Nigerian fintech context per the blueprint:

- **ISO 27001** — global baseline, widely recognised by regulators and partners.
- **PCI DSS** — mandatory for payment processors; cardholder data environment controls.
- **SOC 2** — trust service criteria expected by SaaS vendors and cloud providers.
- **NDPR/NDPA** — Nigeria Data Protection Regulation (2019) + Act (2023); domestic legal requirement.
- **CBN Cybersecurity Framework** — Central Bank of Nigeria's risk-based framework for banks and fintechs.

A full-library assessment (`framework=ALL`) evaluates all 281 controls and produces
per-framework scores in the `framework_scores` field, so a single run covers every
required regime.

## Module 6 — Incident Response Integration notes

`incident-service` is the terminal module in the event chain: it turns high/critical
monitoring alerts into tracked incidents, drives their response lifecycle with an
append-only timeline and an SLA clock, and drafts the Nigerian regulatory
notifications each incident warrants. It *consumes* `monitoring.alerts` (the hub
`monitoring-service` publishes to) and *publishes* `incident.events`. Key endpoints
(all behind the gateway at `/api/incidents/...`):

- `GET /incidents/dashboard` — response posture roll-up: open incidents, open by
  severity and category, SLA-breached count, pending regulatory notifications, and
  mean-time-to-contain. Aggregates over this service's own rows only (same convention
  as the risk/compliance/monitoring dashboards — no cross-service HTTP fan-out).
- `GET /incidents` (filter by `vendor_id` / `status` / `severity`) and
  `POST /incidents` (writer-gated) — list and manually open incidents.
- `GET /incidents/{id}` — full detail: the incident, its timeline, and its drafted
  notifications.
- `POST /incidents/{id}/status` — advance the lifecycle (writer-gated; an illegal
  transition returns 409). `POST /incidents/{id}/assign` and
  `POST /incidents/{id}/notes` record assignment and analyst notes.
- `GET /incidents/{id}/timeline` and `GET /incidents/{id}/notifications` — the
  append-only history and the regulatory drafts on their own.

Read access (list/detail/dashboard/timeline/notifications) is open to any
authenticated role; opening, transitioning, assigning and noting are gated to
`risk_officer` / `ciso` / `admin` (compliance managers consume incidents, they don't
drive response). Every open/transition/assign/note is written to the hash-chained
`audit_log`.

**Lifecycle state machine.** Incidents move `open → investigating → contained →
resolved → closed`. Limited backward transitions are allowed for real-world response
(a contained/resolved incident can be reopened to `investigating` when a finding
recurs); `closed` is terminal. The rules live as pure, unit-tested functions in
`services/lifecycle.py` and are mirrored in the frontend's action buttons. Reaching
`contained`/`resolved`/`closed` stamps the corresponding timestamp (closing without an
explicit resolve stamps both), which feeds mean-time-to-contain.

**SLA clock.** `sla_due_at = opened_at + window`, where the window is keyed off
severity (Critical 24h — mirroring the CBN reporting expectation — High 72h, Medium
168h, Low 336h). An incident is *breached* once it passes its due time while still
active; resolved/closed incidents never breach. This is a computed field
(`is_sla_breached`), so it stays correct without a background job mutating rows.

**Auto-open from monitoring alerts.** The Kafka consumer reacts to `monitoring.alert*`
events: any alert at/above the configured `auto_open_min_severity` (default **High**)
auto-opens an incident, **deduplicated on the originating alert id** (`source_ref`) so
a re-published alert never spawns a duplicate. The alert's `alert_type` maps to an
incident category (e.g. `THREAT_INTEL_MATCH → THREAT_INTEL`, `CRITICAL_CVE →
VULNERABILITY`). Medium/Low alerts are left to the monitoring queue unless an analyst
promotes them manually. All Kafka is fail-soft (the shared producer/consumer no-op
when no broker is reachable), so unit tests and offline demos need no broker.

**Regulatory notifications (CBN + NDPC).** On open, the service drafts the
notifications the incident warrants:

- **CBN** — the Central Bank of Nigeria expects supervised financial institutions to
  report material cyber incidents promptly (24h window). Drafted for every
  High/Critical incident.
- **NDPC** — under the Nigeria Data Protection Act 2023 (and the earlier NDPR), a
  personal-data breach must be notified to the Nigeria Data Protection Commission
  within 72h. Drafted when personal data is involved (category `DATA_BREACH` or an
  explicit analyst flag on manual open).

Drafting is idempotent per regulator and the deterministic draft text is testable and
demoable. **Deviation from spec:** there is no live regulator API integration — a
notification is generated as a reviewable draft with a deadline and a draft/submitted
status, not a real filing. The generators are isolated in `services/notifications.py`,
so wiring a real submission channel behind the same interface is a localised change.

**Event flow.** incident-service *consumes* `monitoring.alerts` and *publishes*
`incident.events` (`incident.opened`, `incident.status_changed`, `incident.resolved`)
so downstream consumers (dashboards, notifiers) can react. The shared Kafka consumer
dispatches every subscribed topic to one handler, mirroring the other services.

## Further reading

- [SECURITY.md](SECURITY.md) — auth posture, encryption, audit log guarantees,
  mock-vs-real adapter posture, and explicit scope trade-offs for this pass.
