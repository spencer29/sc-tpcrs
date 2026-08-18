# Production deployment — single-host Docker

This is the **self-hosted / single-host** production path: the whole stack on
one Docker host, hardened by a compose overlay. For a **managed-cloud** path
(Render web services + managed Postgres) see [RENDER_DEPLOY.md](RENDER_DEPLOY.md).
The two are alternatives; this one keeps Neo4j and Kafka in-cluster, so the SBOM
graph and the event choreography are fully live (Render omits them).

The overlay is [docker-compose.prod.yml](docker-compose.prod.yml). It is applied
**on top of** the base [docker-compose.yml](docker-compose.yml) — the base file
is untouched and still runs the dev stack on its own (`docker compose up`).

## TL;DR

```bash
cp .env.example .env            # then edit — see "Go-live checklist" below
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.yml -f docker-compose.prod.yml --profile tools run --rm seed
```

Then open:
- **SPA (nginx):** http://localhost:8081
- **Gateway (API):** http://localhost:8080 — health at http://localhost:8080/health

No `--profile prod` flag is needed: the overlay clears the `prod` profile on
`frontend-prod` so it starts by default, and parks the dev Vite server behind a
`dev` profile so it does not. Everything else (the 8 services + 4 datastores)
starts as normal.

> Because the overlay filenames must be repeated on every `docker compose`
> invocation, either export `COMPOSE_FILE=docker-compose.yml:docker-compose.prod.yml`
> once in your shell/`.env`, or wrap the command in a shell alias.

## What the overlay changes vs. the dev stack

| Concern | Dev (base) | Prod (overlay) |
|---|---|---|
| **Exposed host ports** | every service + datastore (8001–8007, 5432, 6379, 7474/7687, 9092, 5173) | **only** gateway `:8080` and the SPA `:8081` |
| **Restart policy** | none | `restart: unless-stopped` on all long-running containers |
| **uvicorn workers** | 1 per service | `WEB_CONCURRENCY=2` (stateless services + gateway); **monitoring-service pinned to 1** |
| **Frontend** | Vite dev server on `:5173` | nginx-served static build on `:8081`, `/api` reverse-proxied to the gateway |
| **auth ENV** | `development` | `development` by default; `AUTH_ENV=production` toggle |

### Attack surface

Only two ports are published to the host:

- **`:8080` — gateway.** The authenticated API boundary: HS256 JWT validation +
  a Redis-backed per-minute rate limiter (the counter lives in Redis, so it is
  shared correctly across the 2 workers).
- **`:8081` — frontend-prod (nginx).** Serves the built SPA and reverse-proxies
  `/api/ → gateway:8000` on the internal network, so the browser talks to a
  single same-origin host (no CORS in the default same-origin build).

Every application service (auth/vendor/risk/sbom/compliance/monitoring/incident)
and every datastore (Postgres, Neo4j, Redis, Kafka) is reachable **only on the
internal compose network**. Their container-internal healthchecks are unaffected
(they curl `localhost:8000` inside the container); check them with
`docker compose … ps`.

### Worker model & the monitoring-service exception

`WEB_CONCURRENCY` is read by uvicorn directly (no `command:` override needed), so
the overlay just sets it in each service's environment. It defaults to 2 and is
overridable — e.g. `WEB_CONCURRENCY=4 docker compose -f … up -d` fans every
stateless service out to 4 workers.

**monitoring-service is deliberately pinned to `WEB_CONCURRENCY=1`.** Its FastAPI
lifespan starts a single asyncio sweep loop (the periodic monitoring sweep — see
the "Deviation from spec — scheduler" note in the [README](README.md)). Extra
uvicorn workers would each run their own copy of that loop, duplicating the
sweeps and the alerts they emit. Scale monitoring by running additional
**container replicas** behind the gateway, not by adding workers. (The Kafka
consumers in risk/compliance/incident/monitoring are group-coordinated and
fail-soft, so those *are* safe to run multi-worker.)

## Go-live checklist

The overlay inherits `env_file: .env`; it injects no secrets of its own. Before
exposing this to anything real, edit `.env`:

1. **Rotate secrets.** Replace the `change_me_…` placeholders: `JWT_SECRET`
   (shared HS256 signing key — must match across all services),
   `MFA_SECRET_ENC_KEY`, and the Postgres / Neo4j passwords.
2. **Harden auth.** Set `AUTH_ENV=production`. This disables the dev-only MFA
   helper endpoint (`GET /api/auth/dev/mfa-code`) — so seed/log in with a real
   TOTP authenticator once flipped. Left at `development` by default so the demo
   works out-of-the-box with placeholder secrets.
3. **Lock CORS.** Set `CORS_ALLOWED_ORIGINS` to the real browser origin. In the
   default same-origin setup (SPA proxies `/api` to the gateway) CORS is not
   exercised; it matters only if you point the browser straight at `:8080`.
4. **Front it with TLS.** Terminate HTTPS at a reverse proxy / load balancer in
   front of `:8081` (and `:8080` if you expose the API directly). This overlay
   serves plain HTTP; it assumes something upstream adds TLS.
5. **Cross-origin SPA (optional).** To serve the SPA and API on different hosts,
   rebuild frontend-prod with an absolute API base:
   `FRONTEND_PROD_API_BASE_URL=https://api.example.com/api docker compose -f … build frontend-prod`
   (Vite inlines `VITE_*` at build time), and set `CORS_ALLOWED_ORIGINS` on the
   gateway accordingly.

## Operating the stack

```bash
# Base + overlay on every command (or set COMPOSE_FILE as above):
alias dcp='docker compose -f docker-compose.yml -f docker-compose.prod.yml'

dcp ps                         # status + health of every container
dcp logs -f gateway            # follow one service
dcp --profile tools run --rm seed     # (re)seed demo data through the gateway
dcp up -d --build              # roll out a rebuild (restart policy keeps them up)
dcp down                       # stop the stack (add -v to also drop data volumes)
```

Data persists in the named volumes `postgres-data`, `neo4j-data`, `kafka-data`
(declared in the base file); `dcp down` without `-v` leaves them intact.

## Verifying the overlay

`config` renders the fully-merged model without starting anything — use it to
confirm the ports/workers/restart posture before a deploy:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml config
docker compose -f docker-compose.yml -f docker-compose.prod.yml config --services
```

The rendered model should show `published:` only for `8080` (gateway) and `8081`
(frontend-prod), `WEB_CONCURRENCY: "2"` on the stateless services and `"1"` on
monitoring-service, and `restart: unless-stopped` throughout.

## Build note

The service images use BuildKit cache mounts (`# syntax=docker/dockerfile:1` +
`--mount=type=cache,target=/root/.cache/pip`), which keep the pip wheel cache out
of the image layers while persisting it across services and rebuilds. Modern
Docker (Compose v2+/buildx) enables BuildKit by default; on an older engine,
prefix builds with `DOCKER_BUILDKIT=1`.
