# syntax=docker/dockerfile:1
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
#
# The pip cache mount (--mount=type=cache) keeps the wheel cache OUT of the
# image layer (so images stay slim) while persisting it across services and
# rebuilds, so a wheel is downloaded once, not once per service per build.

FROM python:3.11-slim AS base

WORKDIR /app

# Install the shared library first (changes least often -> best layer cache).
COPY shared/py-common /shared/py-common
RUN --mount=type=cache,target=/root/.cache/pip pip install /shared/py-common

# Install this service's own dependencies.
COPY services/<name>/pyproject.toml ./pyproject.toml
RUN --mount=type=cache,target=/root/.cache/pip pip install -e .

# Copy the rest of the service source.
COPY services/<name> .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
