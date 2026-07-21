#!/usr/bin/env bash
set -Eeuo pipefail

# The integration database is deliberately separate from the persistent demo
# database. This script runs only when PostgreSQL initializes an empty volume.
psql --set ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<'SQL'
SELECT 'CREATE DATABASE reagent_test'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'reagent_test')\gexec
SQL
