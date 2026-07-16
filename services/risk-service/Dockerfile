# See infrastructure/docker/python-service.Dockerfile for the shared pattern
# this is generated from. Build context MUST be the repo root.
FROM python:3.11-slim AS base

WORKDIR /app

# Explicit timeout/retries: this service's dependencies include large
# wheels (xgboost, scikit-learn, numpy) that have been observed to stall
# indefinitely on a slow/flaky connection without these -- a bounded
# per-request timeout lets pip's own retry logic recover instead of hanging.
ENV PIP_DEFAULT_TIMEOUT=60
ENV PIP_RETRIES=10

COPY shared/py-common /shared/py-common
RUN pip install --no-cache-dir /shared/py-common

COPY services/risk-service/pyproject.toml ./pyproject.toml
RUN pip install --no-cache-dir -e .

COPY services/risk-service .

EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
