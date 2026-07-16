# SC-TPCRS — Supply Chain and Third-Party Cybersecurity Risk System

A microservices-based platform for fintech/payment organisations to onboard,
risk-tier, assess, and continuously monitor third-party vendors.

## What's built in this pass

This is the **first build pass** on top of the original blueprint spec, scoped
to: full infrastructure/topology, two fully-implemented modules, and a
working frontend slice. Every design decision and scope trade-off is
documented inline in code and in [SECURITY.md](SECURITY.md) — read those
before assuming a "full" feature is present.

| Module | Service | Status |
|---|---|---|
| Auth (lite Keycloak substitute) | `auth-service` | Full — login, MFA (TOTP), JWT issuance |
| API Gateway (lite Kong substitute) | `gateway` | Full — JWT validation, rate limiting, routing |
| 1. Vendor Lifecycle Management | `vendor-service` | Full |
| 2. Automated Risk Assessment Engine | `risk-service` | Full, including anomaly detection |
| 3. Supply Chain Visibility / SBOM | `sbom-service` | Health-only skeleton (deferred) |
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
        +---> Neo4j (:7474/:7687) -- constraints only this pass, no data yet
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
`risk-service`) has its own pytest suite covering core business logic:
tiering boundaries, state-machine transitions, the VRS weighted formula,
JWT issuance/expiry/role checks, and rate-limit thresholds. This pass
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

## Further reading

- [SECURITY.md](SECURITY.md) — auth posture, encryption, audit log guarantees,
  mock-vs-real adapter posture, and explicit scope trade-offs for this pass.
