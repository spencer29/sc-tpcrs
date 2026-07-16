# One-shot seeding container. Build context MUST be the repo root (see
# infrastructure/docker/python-service.Dockerfile for the pattern this
# mirrors). Run via `docker compose --profile tools run --rm seed` or
# `make seed` -- not part of the default `docker compose up`.
FROM python:3.11-slim AS base

WORKDIR /app

COPY shared/py-common /shared/py-common
RUN pip install --no-cache-dir /shared/py-common

COPY seed/requirements.txt ./seed-requirements.txt
RUN pip install --no-cache-dir -r seed-requirements.txt

COPY seed ./seed

CMD ["python", "-m", "seed.seed_all"]
