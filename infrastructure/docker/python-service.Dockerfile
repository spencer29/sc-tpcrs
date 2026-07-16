# Reference pattern for every SC-TPCRS Python microservice's Dockerfile.
#
# This file is not built directly. Each `services/<name>/Dockerfile` is a
# concrete copy of this pattern with <name> substituted, because Docker
# Compose build args can't parameterize a shared Dockerfile path cleanly
# across differing build contexts. Keep any change here mirrored into every
# service Dockerfile.
#
# IMPORTANT: build context for every service is the REPO ROOT (not the
# service directory), so this Dockerfile can COPY shared/py-common. See each
# service's entry in docker-compose.yml: `build: { context: ., dockerfile: services/<name>/Dockerfile }`.

FROM python:3.11-slim AS base

WORKDIR /app

# Install the shared library first (changes least often -> best layer cache).
COPY shared/py-common /shared/py-common
RUN pip install --no-cache-dir /shared/py-common

# Install this service's own dependencies.
COPY services/<name>/pyproject.toml ./pyproject.toml
RUN pip install --no-cache-dir -e .

# Copy the rest of the service source.
COPY services/<name> .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
