#!/usr/bin/env bash
# Runs once on first Postgres container start (mounted into
# /docker-entrypoint-initdb.d/). Creates one database per backend service,
# all owned by POSTGRES_USER, per .env.example's "one Postgres instance, one
# DB per service" design.
set -euo pipefail

DATABASES=(auth vendor risk sbom compliance monitoring incident)

for db in "${DATABASES[@]}"; do
  echo "Creating database '${db}' (if not exists)..."
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
    SELECT 'CREATE DATABASE ${db} OWNER ${POSTGRES_USER}'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '${db}')\gexec
EOSQL
done
