# See infrastructure/docker/python-service.Dockerfile for the shared pattern
# this is generated from. Build context MUST be the repo root.
FROM python:3.11-slim AS base

WORKDIR /app

COPY shared/py-common /shared/py-common
RUN pip install --no-cache-dir /shared/py-common

COPY services/gateway/pyproject.toml ./pyproject.toml
RUN pip install --no-cache-dir -e .

COPY services/gateway .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
