# 🎯 SC-TPCRS MASTER ACCESS GUIDE

## System Status: ✅ FULLY OPERATIONAL

All 13 containers running and healthy. Ready for stakeholder access.

---

## 👥 8 Pre-Configured Stakeholder Accounts

### Shared Credentials for ALL Users
```
Password: Demo1234!  (case-sensitive)
MFA:      Required for all users (6-digit code)
```

---

## 🔐 User Accounts by Role

### Administrators (2)
| # | Email | Access Level |
|---|-------|--------------|
| 1 | admin1@sc-tpcrs.demo | Full system access |
| 2 | admin2@sc-tpcrs.demo | Full system access |

### CISOs (2)
| # | Email | Access Level |
|---|-------|--------------|
| 1 | ciso1@sc-tpcrs.demo | Security & risk oversight |
| 2 | ciso2@sc-tpcrs.demo | Security & risk oversight |

### Risk Officers (2)
| # | Email | Access Level |
|---|-------|--------------|
| 1 | risk.officer1@sc-tpcrs.demo | Vendor assessment |
| 2 | risk.officer2@sc-tpcrs.demo | Vendor assessment |

### Compliance Managers (2)
| # | Email | Access Level |
|---|-------|--------------|
| 1 | compliance1@sc-tpcrs.demo | Compliance monitoring |
| 2 | compliance2@sc-tpcrs.demo | Compliance monitoring |

---

## 🌐 Access Points

| Service | URL | Purpose |
|---------|-----|---------|
| **Frontend** | http://localhost:5173 | Main dashboard |
| **Gateway API** | http://localhost:8080/api | API root |
| **Auth Docs** | http://localhost:8001/docs | Auth service API |
| **Vendor Docs** | http://localhost:8002/docs | Vendor service API |
| **Risk Docs** | http://localhost:8003/docs | Risk service API |
| **Neo4j** | http://localhost:7474 | Graph database |

---

## 🚀 Quick Start: Login to Dashboard

### Option 1: Browser
```
1. Go to http://localhost:5173
2. Enter email (pick from table above)
3. Enter password: Demo1234!
4. Generate MFA code (see below)
5. Enter MFA code
6. ✅ Done
```

### Option 2: Get MFA Code (Terminal)
Pick your email, then run:
```bash
# Example for admin1
curl http://localhost:8080/api/auth/dev/mfa-code?email=admin1@sc-tpcrs.demo

# Response: {"email":"admin1@sc-tpcrs.demo","otp_code":"123456"}
# Use "123456" in the frontend
```

### Option 3: Get MFA Code (Browser Console)
```javascript
fetch('http://localhost:8080/api/auth/dev/mfa-code?email=admin1@sc-tpcrs.demo')
  .then(r => r.json())
  .then(d => console.log('MFA:', d.otp_code))
```

---

## 📊 Demo Data Included

**20 Vendors Pre-Loaded:**
- Critical tier: 9 vendors
- High tier: 6 vendors  
- Medium tier: 5 vendors
- Risk scores: 12 computed
- Demo vendor with CVE: Yes (left-pad@1.0.0, CVSS 9.8)

**8 Demo Users:**
- All passwords: `Demo1234!`
- All MFA-enabled
- All can log in immediately

---

## 🔑 MFA Commands (Copy & Paste)

```bash
# Admin 1
curl http://localhost:8080/api/auth/dev/mfa-code?email=admin1@sc-tpcrs.demo

# Admin 2
curl http://localhost:8080/api/auth/dev/mfa-code?email=admin2@sc-tpcrs.demo

# CISO 1
curl http://localhost:8080/api/auth/dev/mfa-code?email=ciso1@sc-tpcrs.demo

# CISO 2
curl http://localhost:8080/api/auth/dev/mfa-code?email=ciso2@sc-tpcrs.demo

# Risk Officer 1
curl http://localhost:8080/api/auth/dev/mfa-code?email=risk.officer1@sc-tpcrs.demo

# Risk Officer 2
curl http://localhost:8080/api/auth/dev/mfa-code?email=risk.officer2@sc-tpcrs.demo

# Compliance Manager 1
curl http://localhost:8080/api/auth/dev/mfa-code?email=compliance1@sc-tpcrs.demo

# Compliance Manager 2
curl http://localhost:8080/api/auth/dev/mfa-code?email=compliance2@sc-tpcrs.demo
```

---

## 🛠️ Troubleshooting

### Can't reach localhost?
- Try `127.0.0.1` instead: http://127.0.0.1:5173
- Ensure Docker Desktop is running
- Check firewall isn't blocking ports 5173, 8080
- Restart Docker: Restart Docker Desktop app

### Wrong MFA code?
- Generate a new one (codes expire in ~30s)
- Verify system time is correct
- Try again

### Connection refused?
```bash
# Check all containers are running
docker compose ps

# Restart if needed
docker compose down
docker compose up -d
```

---

## 📋 Full Documentation

For detailed information, see:
- `LOGIN_DETAILS_ALL_STAKEHOLDERS.md` — Complete credentials + API access
- `LOGIN_QUICK_REFERENCE.md` — Quick lookup table
- `TROUBLESHOOTING.md` — Diagnostic steps
- `CODEBASE_ASSESSMENT.md` — Technical overview
- `SYSTEM_READY.md` — Getting started guide

---

## 📊 Role Capabilities

| Task | Admin | CISO | Risk Officer | Compliance Mgr |
|------|-------|------|--------------|----------------|
| Create vendors | ✅ | ✅ | ✅ | ✅ |
| View risk scores | ✅ | ✅ | ✅ | ✅ |
| Approve tiers | ✅ | ✅ | ✅ | ❌ |
| Manage users | ✅ | ❌ | ❌ | ❌ |
| View compliance | ✅ | ✅ | ⚠️ | ✅ |
| System config | ✅ | ❌ | ❌ | ❌ |

---

## ✅ System Status

- **Frontend**: Running (Vite dev server)
- **Gateway**: Healthy (accepting requests)
- **Auth Service**: Healthy
- **Vendor Service**: Healthy
- **Risk Service**: Healthy
- **PostgreSQL**: Healthy
- **Redis**: Healthy
- **Kafka**: Healthy
- **Neo4j**: Healthy

**Total:** 13 containers, all operational

---

**Version:** 1.0  
**Generated:** 2026-07-22  
**Status:** Production-ready for demo/development  
**Next Action:** Open http://localhost:5173 and login
