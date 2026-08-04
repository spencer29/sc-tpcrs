# Quick Reference - Login Card

## All Stakeholder Credentials

| Role | Email | Password | MFA Command |
|------|-------|----------|-------------|
| **Admin** | admin1@sc-tpcrs.demo | Demo1234! | `curl http://localhost:8080/api/auth/dev/mfa-code?email=admin1@sc-tpcrs.demo` |
| **Admin** | admin2@sc-tpcrs.demo | Demo1234! | `curl http://localhost:8080/api/auth/dev/mfa-code?email=admin2@sc-tpcrs.demo` |
| **CISO** | ciso1@sc-tpcrs.demo | Demo1234! | `curl http://localhost:8080/api/auth/dev/mfa-code?email=ciso1@sc-tpcrs.demo` |
| **CISO** | ciso2@sc-tpcrs.demo | Demo1234! | `curl http://localhost:8080/api/auth/dev/mfa-code?email=ciso2@sc-tpcrs.demo` |
| **Risk Officer** | risk.officer1@sc-tpcrs.demo | Demo1234! | `curl http://localhost:8080/api/auth/dev/mfa-code?email=risk.officer1@sc-tpcrs.demo` |
| **Risk Officer** | risk.officer2@sc-tpcrs.demo | Demo1234! | `curl http://localhost:8080/api/auth/dev/mfa-code?email=risk.officer2@sc-tpcrs.demo` |
| **Compliance Mgr** | compliance1@sc-tpcrs.demo | Demo1234! | `curl http://localhost:8080/api/auth/dev/mfa-code?email=compliance1@sc-tpcrs.demo` |
| **Compliance Mgr** | compliance2@sc-tpcrs.demo | Demo1234! | `curl http://localhost:8080/api/auth/dev/mfa-code?email=compliance2@sc-tpcrs.demo` |

## System Access

| Component | URL | Purpose |
|-----------|-----|---------|
| Frontend | http://localhost:5173 | Web dashboard |
| Gateway API | http://localhost:8080/api | API root |
| Neo4j Browser | http://localhost:7474 | Graph database UI |

## Login Flow

1. Open http://localhost:5173
2. Enter email from table above
3. Enter password: `Demo1234!`
4. Run MFA command from table, copy the `otp_code` value
5. Enter MFA code
6. ✅ Login complete

## Service Swagger (Dev/Debug)

- Auth: http://localhost:8001/docs
- Vendor: http://localhost:8002/docs
- Risk: http://localhost:8003/docs
- SBOM: http://localhost:8004/docs
- Compliance: http://localhost:8005/docs
- Monitoring: http://localhost:8006/docs
- Incident: http://localhost:8007/docs

---

**All 8 users share password: `Demo1234!`**  
**System fully operational ✅**
