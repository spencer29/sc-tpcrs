# Deploying SC-TPCRS to Render.com

A native [Render Blueprint](https://render.com/docs/infrastructure-as-code)
([`render.yaml`](render.yaml)) that stands up the whole platform — 8 services +
Postgres + Redis + the React SPA — from one file, no third-party tooling. It is
a faithful translation of [`docker-compose.yml`](docker-compose.yml); where a
compose dependency has no managed Render equivalent (Neo4j, Kafka) the app's
built-in **fail-soft** behaviour is used instead, and every such deviation is
documented below. **All synchronous REST flows, including Demo Scenario 1,
remain fully functional.**

```
Internet
  │
  ├─▶ sctpcrs-frontend  (static site, public)         React SPA, VITE_API_BASE_URL → gateway
  │
  └─▶ sctpcrs-gateway   (web service, public)          JWT check · rate limit · routing
          │  private network (region-local)
          ├─▶ sctpcrs-auth         (pserv :8000)        ┐
          ├─▶ sctpcrs-vendor       (pserv :8000)        │
          ├─▶ sctpcrs-risk         (pserv :8000)        │ 7 backends, no public URL
          ├─▶ sctpcrs-sbom         (pserv :8000)        │
          ├─▶ sctpcrs-compliance   (pserv :8000)        │
          ├─▶ sctpcrs-monitoring   (pserv :8000)        │
          └─▶ sctpcrs-incident     (pserv :8000)        ┘
                    │                         │
                    ▼                         ▼
          sctpcrs-postgres           sctpcrs-redis
          (1 instance, 7 DBs)        (Key Value)
```

---

## 1. Compose → Render mapping

| docker-compose service | Render resource | Notes |
|---|---|---|
| `postgres` (16, 7 DBs) | **Database** `sctpcrs-postgres` | One instance; default DB `auth`, other 6 created once (step 4). |
| `redis` | **Key Value** `sctpcrs-redis` (`type: keyvalue`) | Private (`ipAllowList: []`). Used by gateway + risk-service. |
| `gateway` (:8080→8000) | **Web service** `sctpcrs-gateway` (public) | The only public API entry point. `PORT=8000`. |
| `auth/vendor/risk/sbom/compliance/monitoring/incident` | **Private services** (`pserv`) `sctpcrs-<name>` | Internal only, reachable at `http://sctpcrs-<name>:8000`. |
| `frontend` (Vite :5173) | **Static site** `sctpcrs-frontend` (public) | `npm run build` → `dist/`, SPA rewrite to `index.html`. |
| `neo4j` / `neo4j-init` | *(omitted)* | No managed Neo4j. `NEO4J_ENABLED=false` on sbom-service — see §7. |
| `kafka` | *(omitted)* | No managed Kafka. Fail-soft no-op — see §7. |
| `seed` (tools profile) | *(run on demand)* | Run the seed image against the public gateway — see step 5. |

Everything shares one `region` (default `oregon` in the blueprint). Private
networking and the internal database URL only work **within a single region** —
if you change it, change it on every entry in [`render.yaml`](render.yaml).

---

## 2. Prerequisites

- A Render account, and this repository connected to it (GitHub/GitLab).
- Docker locally (only for the optional seed step; everything else builds on Render).
- `psql` available somewhere with network reach to the database (step 4) — your
  machine, or a Render Shell.

---

## 3. Deploy

1. **Push** this repo (with `render.yaml` at the root) to your Git host.
2. In the Render Dashboard: **New ▸ Blueprint**, pick the repo. Render parses
   `render.yaml` and lists all resources. **Apply**.
3. Render provisions the Postgres instance, the Key Value store, and builds all
   9 services. The first build compiles Python wheels (risk-service pulls
   xgboost/scikit-learn/scipy — allow a few minutes); the trained model
   (`services/risk-service/app/ml/model.pkl`) ships in the image, so no runtime
   training happens.
4. Set the two prompted secrets (§5). The 6 non-`auth` backends will **crash-loop
   until their databases exist** — that is expected; finish step 4 and they go
   green on the next restart.

### 4. Create the other 6 databases (one time)

Render Blueprints declare only one database per instance, but one instance hosts
many. Create the rest with the bundled helper (mirrors
`infrastructure/postgres/init-databases.sh`):

```sh
# From your machine: add your IP to sctpcrs-postgres ▸ Access Control first,
# then use the instance's EXTERNAL connection string (ends in .render.com):
DATABASE_URL="postgresql://sctpcrs:<PASSWORD>@<HOST>.oregon-postgres.render.com/auth" \
  sh scripts/render_createdbs.sh

# …or from a Render Shell on any service (same region), use the INTERNAL URL —
# no Access-Control change needed:
DATABASE_URL="postgresql://sctpcrs:<PASSWORD>@dpg-xxxxx:5432/auth" \
  sh scripts/render_createdbs.sh
```

It creates `vendor, risk, sbom, compliance, monitoring, incident` (idempotent)
and prints the 7 databases for confirmation. Then **Manual Deploy ▸ Restart** any
backend that crash-looped. Use the plain `postgresql://` scheme here (that's what
`psql` speaks); the services rewrite it to `postgresql+asyncpg://` themselves (§6).

### 5. Post-deploy secrets

Two values are intentionally **not** auto-generated (`sync: false` in the blueprint):

- **`MFA_SECRET_ENC_KEY`** (auth-service) — a Fernet key. `generateValue` can't
  produce a valid one. Generate and paste it:
  ```sh
  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
  ```
- **`CORS_ALLOWED_ORIGINS`** (gateway) — set to your static site's URL once Render
  assigns it, e.g. `https://sctpcrs-frontend.onrender.com`, then redeploy the
  gateway. (Kept manual to avoid a gateway↔frontend reference cycle. Browsers
  block SPA `fetch()` without this; server-to-server calls are unaffected.)

> **`JWT_SECRET`** is auto-generated once in the `sctpcrs-shared` environment
> group and shared by every service. If your account rejects `generateValue`
> inside a group at apply time, remove that entry and set `JWT_SECRET` once on
> the group in the dashboard — any 44-char random string works.

### 6. Seed demo data (optional but recommended)

The seed script self-mints an admin JWT from `JWT_SECRET` and drives the **real**
onboarding workflow, so questionnaire/risk scores are genuine. Point it at the
public gateway (all traffic then flows gateway → private services):

```sh
# Copy JWT_SECRET from Render: Environment Groups ▸ sctpcrs-shared ▸ JWT_SECRET
docker build -f seed/Dockerfile -t sctpcrs-seed .
docker run --rm \
  -e JWT_SECRET="<the value from the sctpcrs-shared group>" \
  -e AUTH_SERVICE_URL="https://<gateway>.onrender.com/api" \
  -e VENDOR_SERVICE_URL="https://<gateway>.onrender.com/api" \
  -e RISK_SERVICE_URL="https://<gateway>.onrender.com/api" \
  sctpcrs-seed
```

This works because (a) `auth/dev/seed-users` is a gateway public path and
auth-service runs `ENV=development`, and (b) the routers own their `/auth`,
`/vendors`, `/risk` prefixes, so `<gateway>/api/...` reaches them unchanged. If
you hit HTTP 429, raise `GATEWAY_RATE_LIMIT_PER_MIN` on the gateway temporarily.

*Quick alternative (demo login users only, no vendor data):*
`curl -X POST https://<gateway>.onrender.com/api/auth/dev/seed-users`.

### 7. Verify (Demo Scenario 1)

- `https://<gateway>.onrender.com/health` → `{"status":"ok"}`.
- Open the static site, log in with a seeded demo user (grab the MFA code via
  `GET https://<gateway>.onrender.com/api/auth/dev/mfa-code/<username>`, exposed
  because `ENV=development`).
- Open the demo vendor — VRS shows the planted CVSS 9.8 / KEV-listed critical CVE
  and its tier. `GET /api/sbom/graph` returns an **empty** graph (Neo4j disabled)
  rather than an error — that is the documented degradation, not a failure.

---

## How `DATABASE_URL` is composed (design note)

The app requires `postgresql+asyncpg://…/<its-own-db>`, but Render's
`fromDatabase.connectionString` yields `postgresql://…/auth` (default DB, no
async driver). Each backend therefore receives the raw string as `DB_CONN` plus
its own `APP_DB_NAME`, and its `dockerCommand` rewrites both at start-up with
POSIX parameter expansion before migrations/uvicorn run:

```sh
base="${DB_CONN#postgresql://}"   # strip scheme  → user:pass@host:port/auth
base="${base%/*}"                 # strip /auth    → user:pass@host:port
export DATABASE_URL="postgresql+asyncpg://${base}/${APP_DB_NAME}"
```

`asyncpg` is the only DB driver in every service; Alembic here uses the **async**
engine (`async_engine_from_config`), so this one URL serves both migrations and
runtime — no `psycopg2`/sync URL needed. sbom-service has no Alembic dir and
creates its tables in-app, so its command skips `alembic upgrade head`.

---

## Documented deviations vs docker-compose

Consistent with the project's "closest faithful equivalent behind an interface,
documented" principle:

1. **No managed Neo4j → graph mirror disabled.** sbom-service is the only Neo4j
   writer and is fully fail-soft: `NEO4J_ENABLED=false` keeps CycloneDX/SPDX
   ingestion and CVE cross-referencing intact; `/api/sbom/graph` returns an empty
   graph and `/health` reports `neo4j: false`. (GDS analytics already run on
   `networkx`, not Neo4j — unchanged from compose.) See §7 opt-in below.
2. **No managed Kafka → event choreography no-op.** The `KafkaEventProducer`/
   `Consumer` wrappers catch `KafkaConnectionError` and degrade to no-ops (the
   consumer simply never starts; the HTTP API is unaffected).
   `KAFKA_BOOTSTRAP_SERVERS=localhost:9092` gives a fast connection-refused.
   **Impact:** the *asynchronous* cross-module chain goes quiet — e.g. a
   monitoring alert no longer *auto-*opens an incident via an event. Every
   equivalent **synchronous** REST path still works (analysts open/drive
   incidents directly; risk recompute is a direct call), so all demo scenarios
   remain functional. Opt-in below.
3. **`ENV=development` on auth-service.** Enables `/auth/dev/seed-users` and the
   MFA-code lookup the seed job and demo login rely on. See Security notes.
4. **`PORT` pinned to 8000.** Every process binds `:8000`; Render's default
   expectation is 10000, overridden via `PORT` (verified supported).
5. **Backends are private services (`pserv`), not free web services.** Preserves
   the compose topology (gateway is the sole entry) and avoids free-tier cold
   starts breaking inter-service calls. See Cost.

## Security notes

- `ENV=development` exposes auth-service's dev convenience endpoints
  (`/auth/dev/*`). Fine for a demo; for a hardened deployment set `ENV=production`
  and seed users through a private one-off job instead of the public dev endpoint.
- Backends carry no public URL (private network only). The gateway enforces JWT +
  rate limiting; keep `CORS_ALLOWED_ORIGINS` pinned to the SPA origin.
- Rotate `JWT_SECRET`/`MFA_SECRET_ENC_KEY` from the dashboard for anything beyond a demo.

## Cost

Postgres (`free`), Key Value (`free`), and the static site (free) cost nothing on
the demo tiers, but the free Postgres expires (~30 days) and has size caps. The
1 web + 7 private services are on `starter` (paid) because private services have
no free tier and a gateway shouldn't cold-start. **Budget variant:** for a
throwaway demo you can retype the backends as `type: web` with `plan: free`
(public URLs + cold starts, and you'd wire the 7 `*_SERVICE_URL` to the new
public hostnames) — cheaper, but no longer the faithful private topology.

## Opt back in: Neo4j / Kafka

- **Neo4j** — run Neo4j Aura (or a self-managed instance), then on sbom-service
  set `NEO4J_ENABLED=true`, `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`. Ingestion
  starts mirroring to the graph again; `/api/sbom/graph` populates.
- **Kafka** — run a broker reachable on the private network (e.g. a `pserv` from
  `apache/kafka:3.7.0`, or a hosted broker), then set `KAFKA_BOOTSTRAP_SERVERS`
  in the `sctpcrs-shared` group to its `host:9092`. The event chain reactivates
  automatically — no code change (the wrappers connect lazily).

## Troubleshooting

- **A backend keeps restarting** → its database isn't created yet (step 4) or
  `alembic upgrade head` can't connect. Check the database exists and restart.
- **SPA loads but every API call fails in the browser** → `CORS_ALLOWED_ORIGINS`
  on the gateway doesn't match the static site origin (step 5). `curl` works
  regardless (CORS is browser-only), which isolates it quickly.
- **`RuntimeError: JWT_SECRET environment variable is not set`** → the service
  isn't attached to the `sctpcrs-shared` group, or the group value is empty.
- **Static build can't reach the API** → confirm `VITE_API_BASE_URL` baked at
  build time; rebuild the static site after the gateway URL is known.
