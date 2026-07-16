from __future__ import annotations

import os

AUTH_SERVICE_URL = os.environ.get("AUTH_SERVICE_URL", "http://auth-service:8000")
VENDOR_SERVICE_URL = os.environ.get("VENDOR_SERVICE_URL", "http://vendor-service:8000")
RISK_SERVICE_URL = os.environ.get("RISK_SERVICE_URL", "http://risk-service:8000")

# .env.example's default was lowered from 50 to 20 for this build pass, so a
# full `docker compose --profile tools run --rm seed` stays fast; raise it
# back up (and extend seed/vendor_templates.py with more entries) for a
# fuller demo dataset later.
SEED_VENDOR_COUNT = int(os.environ.get("SEED_VENDOR_COUNT", "20"))
SEED_RANDOM_SEED = int(os.environ.get("SEED_RANDOM_SEED", "42"))
