#!/usr/bin/env bash
# Live Demo Scenario 1 verification through the gateway (:8080).
# Login -> MFA -> ingest left-pad SBOM -> assert CVE-2024-99999 Critical/KEV/Act.
set -euo pipefail
GW="http://localhost:8080"
EMAIL="risk.officer1@sc-tpcrs.demo"
PASS="Demo1234!"

echo "== ensure demo users exist =="
curl -s -X POST "$GW/api/auth/dev/seed-users" >/dev/null || true

echo "== password login =="
BRIDGE=$(curl -s -X POST "$GW/api/auth/login" \
  -H 'Content-Type: application/json' \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASS\"}" \
  | python -c 'import sys,json;print(json.load(sys.stdin)["mfa_bridge_token"])')
echo "bridge token: ${BRIDGE:0:24}..."

echo "== fetch dev MFA code =="
OTP=$(curl -s "$GW/api/auth/dev/mfa-code?email=$EMAIL" \
  | python -c 'import sys,json;print(json.load(sys.stdin)["otp_code"])')
echo "otp: $OTP"

echo "== mfa verify -> access token =="
TOKEN=$(curl -s -X POST "$GW/api/auth/mfa/verify" \
  -H 'Content-Type: application/json' \
  -d "{\"mfa_bridge_token\":\"$BRIDGE\",\"otp_code\":\"$OTP\"}" \
  | python -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')
echo "access token: ${TOKEN:0:24}..."

VENDOR_ID="11111111-1111-1111-1111-111111111111"
SBOM=$(python - <<'PY'
import json
print(json.dumps({
  "bomFormat":"CycloneDX","specVersion":"1.6",
  "metadata":{"component":{"name":"live-demo-app","type":"application"}},
  "components":[
    {"type":"library","name":"left-pad","version":"1.0.0","purl":"pkg:npm/left-pad@1.0.0"},
    {"type":"library","name":"express","version":"4.18.2","purl":"pkg:npm/express@4.18.2"}
  ]
}))
PY
)
REQ=$(python - "$VENDOR_ID" "$SBOM" <<'PY'
import json,sys
print(json.dumps({"vendor_id":sys.argv[1],"content":sys.argv[2],"document_name":"live-demo.cdx.json"}))
PY
)

echo "== ingest SBOM via gateway =="
RESP=$(curl -s -X POST "$GW/api/sbom/ingest" \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d "$REQ")
echo "$RESP" | python -m json.tool | head -60

echo "== assert Demo Scenario 1 =="
RESP="$RESP" python - <<'PY'
import os,json
r=json.loads(os.environ["RESP"])
crit=r["critical_vulnerabilities"]
p=[v for v in crit if v["cve_id"]=="CVE-2024-99999"]
assert p, f"CVE-2024-99999 not in critical set: {[v['cve_id'] for v in crit]}"
v=p[0]
assert v["severity"]=="Critical", v
assert v["kev_flag"] is True, v
assert v["ssvc_priority"]=="Act", v
print(f"PASS: CVE-2024-99999 severity={v['severity']} kev={v['kev_flag']} ssvc={v['ssvc_priority']} processing_ms={r['processing_ms']}")
PY

echo "== CVE impact (blast radius) via gateway =="
curl -s "$GW/api/sbom/graph/cve/CVE-2024-99999/impact" \
  -H "Authorization: Bearer $TOKEN" \
  | python -c 'import sys,json;d=json.load(sys.stdin);print("affected components:",[c["component_name"] for c in d])'
