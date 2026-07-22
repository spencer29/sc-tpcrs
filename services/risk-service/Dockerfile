# See infrastructure/docker/python-service.Dockerfile for the shared pattern
# this is generated from. Build context MUST be the repo root.
FROM python:3.11-slim AS base

WORKDIR /app

RUN pip install --upgrade pip setuptools

# Explicit timeout/retries: this service's dependencies include large
# wheels (xgboost, scikit-learn, numpy) that have been observed to stall
# indefinitely on a slow/flaky connection without these -- a bounded
# per-request timeout lets pip's own retry logic recover instead of hanging.
ENV PIP_DEFAULT_TIMEOUT=120
ENV PIP_RETRIES=5
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

COPY shared/py-common /shared/py-common
RUN pip install --no-cache-dir /shared/py-common

COPY services/risk-service/pyproject.toml ./pyproject.toml
RUN pip install --no-cache-dir -e .

COPY services/risk-service .

EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
