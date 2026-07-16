# SC-TPCRS Security Posture

This document records the security-relevant design decisions for this build
pass, including deliberate scope trade-offs relative to the full blueprint
spec (Kong, Keycloak, OWASP ASVS Level 2 hardening, full pen-test cycle,
etc.), so a reviewer can see what's real, what's a placeholder, and why.

## Authentication & Identity

**HS256 shared-secret JWT, not Keycloak/OIDC.** Every service independently
validates access tokens using a single shared `JWT_SECRET` via
`sc_tpcrs_common.jwt_shared` — no network round-trip to `auth-service` is
required to verify a token, and the gateway *and* each downstream service
both re-validate (defense in depth).

- **Production upgrade path**: swap HS256 for RS256 with a JWKS endpoint on
  `auth-service`, so services verify against a public key instead of holding
  the signing secret. This is a drop-in change in `jwt_shared.py` — the
  `TokenPayload`/`decode_token`/`require_role` call sites do not need to
  change.
- Access tokens expire in 15 minutes (`JWT_ACCESS_TTL_MINUTES`); the
  password→MFA-bridge-token→MFA-verify flow uses a separate 5-minute
  `mfa_bridge` token type so a captured bridge token can't be replayed as an
  access token (`decode_token(expected_type=...)` enforces this).
- MFA (TOTP, RFC 6238) is mandatory for every seeded user. Secrets are
  encrypted at rest with Fernet, using a key deterministically derived
  (sha256) from `MFA_SECRET_ENC_KEY` — this tolerates the human-readable
  placeholder value in `.env.example` without requiring operators to
  hand-generate a properly-formatted 32-byte base64 Fernet key; rotating the
  key is just changing that env var.
- **Not implemented this pass**: account lockout after N failed attempts
  (the blueprint's PCI DSS Req 8.3 control). The gateway's per-identifier
  login rate limit (`GATEWAY_LOGIN_RATE_LIMIT_PER_MIN`, default 5/min) is
  the practical anti-brute-force control for this pass; a dedicated lockout
  counter (via `RedisCache.incr_with_ttl`, same mechanism) is a small
  follow-up.
- Dev-only endpoints (`/auth/dev/mfa-code`, `/auth/dev/seed-users`) return
  404 unless `ENV=development` is set. They exist purely so this prototype
  is demoable without a real authenticator app or a hand-run seeding
  script with direct DB access. **Do not set `ENV=development` in any
  environment reachable from outside a developer's machine.**

## API Gateway (Kong substitute)

The blueprint calls for Kong; this pass uses a small FastAPI reverse proxy
(`services/gateway`) that implements the subset of Kong's behavior this
system actually needs:
- JWT validation on every path except an explicit public allowlist
  (`/api/auth/login`, `/api/auth/mfa/verify`, `/api/auth/dev/*`).
- Per-identifier (JWT `sub`, or client IP if unauthenticated) rate limiting
  via `RedisCache.incr_with_ttl` — general limit and a tighter login-specific
  limit.
- Path-prefix routing to the correct upstream service, injecting
  `X-User-Id`/`X-User-Role` headers downstream.
- **Not implemented**: IP allowlisting for admin APIs, request-size limits,
  WAF-style pattern blocking (SSRF/injection request termination), circuit
  breaking. These are Kong plugins with no equivalent here yet.
- **Fails closed on Redis outage**: if the rate limiter can't reach Redis,
  requests error out (5xx) rather than passing through unmetered. This is a
  deliberate deviation from `redis_cache.py`'s general "degrade, don't
  crash" philosophy — for a rate limiter specifically, failing open would
  defeat its purpose during exactly the kind of load event it exists to
  contain.

## Data Protection

- Password hashes: bcrypt via `passlib`.
- MFA secrets: Fernet-encrypted at rest (see above).
- Hash-chained audit log (`sc_tpcrs_common.audit_log`): every service owns
  its own `audit_log` table (`actor, action, resource, details, recorded_at,
  prev_hash, hash`); `verify_chain()` can detect any row's tampering or
  reordering after the fact. This is an integrity control, not a
  confidentiality one — it does not encrypt audit entries, and a DB-level
  attacker with write access could still forge a *self-consistent* new
  chain from a chosen point forward (a real hardening would forward audit
  rows to an external, append-only store immediately on write; not done
  this pass).
- Transport encryption (TLS) is **not** configured for local
  docker-compose — all inter-service and browser traffic is plaintext HTTP
  on the docker-compose bridge network / localhost. Production deployment
  would need TLS termination (e.g. at the gateway or an ingress) before
  this is internet-facing.
- Vendor documents are stored on local disk
  (`infrastructure/data/vendor-documents/`), not S3/MinIO, behind a
  `FileStore` protocol so a `MinioFileStore` is a drop-in swap later.

## External Adapters (mock/real)

Every external integration (NVD, CISA KEV, MISP, Shodan, AbuseIPDB) is
accessed only through `sc_tpcrs_common.adapters.registry.get_adapter()`,
which reads `{KEY}_MODE` (`mock`|`real`) from the environment. This pass
ships **mock implementations only** — deterministic, seeded via SHA256 (not
Python's randomized `hash()`) so demo runs are reproducible, and
schema-shaped identically to the real APIs so flipping `*_MODE=real` later
requires no downstream parsing changes. `_fetch_real()` raises
`NotImplementedError` with a clear message until a real integration is
wired up. **No real external API calls are made by this system as shipped.**

## Vulnerability & Anomaly Detection Scope

- `risk-service`'s "vulnerability exposure" VRS category reads from a
  seed-populated `vendor_tech_stack` stub table, not real SBOM parsing
  (`sbom-service` is deferred). This is documented tech debt: a future pass
  replaces this table with `SBOM_INGESTION_EVENTS` consumption.
- The XGBoost anomaly-detection model is trained once on ~800 synthetic,
  seeded samples (not the blueprint's 10,000) and its artifact
  (`services/risk-service/app/ml/model.pkl` + `metrics.json`) is committed
  to git rather than trained at container-build time — see that directory's
  README for retraining instructions.

## Testing & CI Scope

CI (`.github/workflows/ci.yml`) runs `pytest` per fully-built Python
service against mocked/SQLite-backed test doubles — **no live Postgres,
Kafka, Neo4j, or Redis in CI this pass**. Tests target realistic coverage
of core business logic (~60-70%), not a repo-wide 80% target. No automated
SAST/DAST/dependency scanning (Bandit, OWASP ZAP, Trivy) is wired into CI
this pass, despite being called for in the original blueprint — flagged
here explicitly as deferred, not silently dropped.
