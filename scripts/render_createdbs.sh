#!/usr/bin/env sh
# =============================================================================
# render_createdbs.sh -- create the 6 additional SC-TPCRS databases on a single
# Render Postgres instance (the 7th, `auth`, is the instance's default DB).
#
# Render Blueprints can declare only ONE database per Postgres instance, but a
# single instance can host many. This one-time step mirrors what
# infrastructure/postgres/init-databases.sh does for docker-compose.
#
# Usage (run ONCE after the Blueprint's Postgres is live):
#
#   # Option A -- from your machine (add your IP to the DB's ipAllowList first),
#   # using the instance's EXTERNAL connection string:
#   DATABASE_URL="postgresql://sctpcrs:PASS@HOST.oregon-postgres.render.com/auth" \
#     sh scripts/render_createdbs.sh
#
#   # Option B -- from a Render Shell on any service in the same region, using
#   # the INTERNAL connection string (no ipAllowList change needed):
#   DATABASE_URL="postgresql://sctpcrs:PASS@dpg-xxxx:5432/auth" \
#     sh scripts/render_createdbs.sh
#
# Requires the `psql` client. Note the plain `postgresql://` scheme here (psql),
# NOT the `postgresql+asyncpg://` the app uses -- the services rewrite the
# scheme themselves at start-up.
#
# Idempotent: a database that already exists is reported and skipped, not fatal.
# =============================================================================
set -eu

: "${DATABASE_URL:?Set DATABASE_URL to the Render Postgres connection string (see usage in this file).}"

DATABASES="vendor risk sbom compliance monitoring incident"

echo "Target instance (default DB 'auth' already exists)."
for db in $DATABASES; do
  printf 'Creating database "%s" ... ' "$db"
  # The connecting user (sctpcrs) becomes the owner by default.
  if psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -c "CREATE DATABASE \"$db\";" >/dev/null 2>&1; then
    echo "created."
  else
    echo "already exists (or not creatable) -- skipped."
  fi
done

echo
echo "Verifying the 7 SC-TPCRS databases are present:"
psql "$DATABASE_URL" -tAc \
  "SELECT datname FROM pg_database WHERE datname IN ('auth','vendor','risk','sbom','compliance','monitoring','incident') ORDER BY datname;"

echo
echo "Done. Restart any backend services that crash-looped while their database did not yet exist."
