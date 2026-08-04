# SC-TPCRS Login Details for All Stakeholders

## System Access Information

**Frontend URL:** http://localhost:5173  
**Gateway API:** http://localhost:8080/api  
**System Status:** ✅ All services operational

---

## Admin Users

### Admin 1 (Primary Administrator)
```
Email:              admin1@sc-tpcrs.demo
Password:           Demo1234!
Role:               admin
Permissions:        Full system access, user management, configuration
MFA Code:           GET /api/auth/dev/mfa-code?email=admin1@sc-tpcrs.demo
Status:             Active
```

### Admin 2 (Secondary Administrator)
```
Email:              admin2@sc-tpcrs.demo
Password:           Demo1234!
Role:               admin
Permissions:        Full system access, user management, configuration
MFA Code:           GET /api/auth/dev/mfa-code?email=admin2@sc-tpcrs.demo
Status:             Active
```

---

## CISO (Chief Information Security Officer) Users

### CISO 1 (Primary)
```
Email:              ciso1@sc-tpcrs.demo
Password:           Demo1234!
Role:               ciso
Permissions:        Security oversight, risk assessment review, compliance monitoring
MFA Code:           GET /api/auth/dev/mfa-code?email=ciso1@sc-tpcrs.demo
Status:             Active
Responsibility:     Vendor security posture, threat intelligence, incident response
```

### CISO 2 (Secondary)
```
Email:              ciso2@sc-tpcrs.demo
Password:           Demo1234!
Role:               ciso
Permissions:        Security oversight, risk assessment review, compliance monitoring
MFA Code:           GET /api/auth/dev/mfa-code?email=ciso2@sc-tpcrs.demo
Status:             Active
Responsibility:     Backup security oversight, incident management
```

---

## Risk Officers

### Risk Officer 1 (Primary Assessment Officer)
```
Email:              risk.officer1@sc-tpcrs.demo
Password:           Demo1234!
Role:               risk_officer
Permissions:        Vendor risk assessment, questionnaire review, risk scoring
MFA Code:           GET /api/auth/dev/mfa-code?email=risk.officer1@sc-tpcrs.demo
Status:             Active
Responsibility:     Vendor onboarding, risk tiering, assessment workflows
```

### Risk Officer 2 (Secondary Assessment Officer)
```
Email:              risk.officer2@sc-tpcrs.demo
Password:           Demo1234!
Role:               risk_officer
Permissions:        Vendor risk assessment, questionnaire review, risk scoring
MFA Code:           GET /api/auth/dev/mfa-code?email=risk.officer2@sc-tpcrs.demo
Status:             Active
Responsibility:     Backup risk assessment, vendor communication
```

---

## Compliance Managers

### Compliance Manager 1 (Primary)
```
Email:              compliance1@sc-tpcrs.demo
Password:           Demo1234!
Role:               compliance_manager
Permissions:        Compliance monitoring, document review, regulatory alignment
MFA Code:           GET /api/auth/dev/mfa-code?email=compliance1@sc-tpcrs.demo
Status:             Active
Responsibility:     Compliance verification, audit trails, regulatory reporting
```

### Compliance Manager 2 (Secondary)
```
Email:              compliance2@sc-tpcrs.demo
Password:           Demo1234!
Role:               compliance_manager
Permissions:        Compliance monitoring, document review, regulatory alignment
MFA Code:           GET /api/auth/dev/mfa-code?email=compliance2@sc-tpcrs.demo
Status:             Active
Responsibility:     Backup compliance checks, documentation management
```

---

## Login Instructions

### Step 1: Access Frontend
```
Open browser → http://localhost:5173
```

### Step 2: Enter Credentials
```
Email:    [Select user from above]
Password: Demo1234!
```

### Step 3: Generate MFA Code
Copy the appropriate API URL and execute in terminal:
```bash
curl http://localhost:8080/api/auth/dev/mfa-code?email=<YOUR_EMAIL>
```

Or use browser console (JavaScript):
```javascript
fetch('http://localhost:8080/api/auth/dev/mfa-code?email=admin1@sc-tpcrs.demo')
  .then(r => r.json())
  .then(d => console.log('MFA Code:', d.otp_code))
```

### Step 4: Complete MFA
```
Enter MFA code from Step 3
```

### Step 5: Login Success
You will be redirected to the dashboard

---

## Role Permissions Matrix

| Feature | Admin | CISO | Risk Officer | Compliance Manager |
|---------|-------|------|--------------|-------------------|
| Vendor Onboarding | ✅ | ✅ | ✅ | ✅ |
| Risk Assessment | ✅ | ✅ | ✅ | ⚠️ (View-only) |
| Compliance Review | ✅ | ✅ | ⚠️ (View-only) | ✅ |
| User Management | ✅ | ⚠️ (Limited) | ❌ | ❌ |
| System Configuration | ✅ | ❌ | ❌ | ❌ |
| Incident Response | ✅ | ✅ | ⚠️ (Report) | ⚠️ (Report) |
| Dashboard Access | ✅ | ✅ | ✅ | ✅ |
| Risk Dashboard | ✅ | ✅ | ✅ | ✅ |

---

## Common Tasks by Role

### Administrators
- User account management
- System configuration
- Infrastructure monitoring
- Access control
- Audit log review

### CISOs
- Security posture assessment
- Risk score review and approval
- Threat intelligence monitoring
- Incident escalation
- Compliance verification

### Risk Officers
- Vendor questionnaire distribution
- Risk score calculation
- Onboarding workflow management
- Vendor communication
- Risk tiering adjustments

### Compliance Managers
- Document compliance verification
- Regulatory alignment checks
- Audit trail monitoring
- Compliance report generation
- Documentation management

---

## Demo Data

**20 Vendors Pre-Loaded:**
- Critical tier vendors: 9
- High tier vendors: 6
- Medium tier vendors: 5
- Risk scores computed: 12
- Demo vendor with known CVE: Yes (left-pad@1.0.0)

**Sample Vendor:**
```
Name:           Demo Critical Vendor (left-pad)
Tier:           Critical
Status:         ONBOARDED
VRS Score:      22.25
Risk Tier:      Low
Known CVE:      Yes (CVSS 9.8)
```

---

## API Access (For Developers)

### Direct Service Swagger UIs
```
Auth Service:       http://localhost:8001/docs
Vendor Service:     http://localhost:8002/docs
Risk Service:       http://localhost:8003/docs
SBOM Service:       http://localhost:8004/docs
Compliance Service: http://localhost:8005/docs
Monitoring Service: http://localhost:8006/docs
Incident Service:   http://localhost:8007/docs
```

### Gateway API (Requires JWT Token)
```
Base URL: http://localhost:8080/api
Auth:     Bearer <JWT_TOKEN>
```

### Getting an API Token (cURL)
```bash
# 1. Login
RESPONSE=$(curl -s -X POST http://localhost:8080/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin1@sc-tpcrs.demo","password":"Demo1234!"}')

# Extract bridge token
BRIDGE_TOKEN=$(echo $RESPONSE | jq -r '.bridge_token')

# 2. Get MFA code
MFA_CODE=$(curl -s "http://localhost:8080/api/auth/dev/mfa-code?email=admin1@sc-tpcrs.demo" | jq -r '.otp_code')

# 3. Verify MFA
JWT_RESPONSE=$(curl -s -X POST http://localhost:8080/api/auth/mfa/verify \
  -H "Content-Type: application/json" \
  -d "{\"bridge_token\":\"$BRIDGE_TOKEN\",\"otp_code\":\"$MFA_CODE\"}")

# Extract JWT
JWT_TOKEN=$(echo $JWT_RESPONSE | jq -r '.access_token')

# 4. Use JWT for API calls
curl -s http://localhost:8080/api/vendors \
  -H "Authorization: Bearer $JWT_TOKEN" | jq .
```

---

## Troubleshooting Login

### "Connection refused"
- Ensure all containers are running: `docker compose ps`
- Check Docker Desktop is running
- Restart services: `docker compose down && docker compose up -d`

### "Invalid credentials"
- Verify email spelling exactly as listed above
- Confirm password is `Demo1234!` (case-sensitive)
- Check user exists in system

### "MFA code doesn't work"
- Regenerate code (expires after ~30s)
- Ensure you copy the entire 6-digit code
- Check system time is synchronized

### "Gateway unreachable"
- Try `http://127.0.0.1:8080` instead of `localhost`
- Check firewall isn't blocking port 8080
- Try accessing via Windows host IP (use `ipconfig`)

---

## Session Management

**Session Timeout:**
- Access Token: 15 minutes
- Refresh Token: 7 days
- Idle Timeout: 30 minutes

**Security Notes:**
- All passwords are for demo/development only
- MFA is mandatory for all users
- JWT tokens are HS256 signed (dev) / RS256 signed (production)
- Rate limiting: 100 req/min general, 5 req/min login

---

## Support

For issues or access problems:
1. Check `./TROUBLESHOOTING.md` for system diagnostics
2. Review logs: `docker compose logs -f <service>`
3. Verify network connectivity: `docker compose ps`
4. Check dashboard: http://localhost:5173

---

**Generated:** 2026-07-22  
**Status:** All systems operational  
**Credentials:** Demo/development use only
