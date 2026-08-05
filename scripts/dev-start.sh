#!/usr/bin/env bash
set -euo pipefail

task_repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
task_runtime_dir="${REAGENT_LOCAL_RUNTIME_DIR:-/tmp/reagent-v0-1-${UID}}"
task_backend_port="${REAGENT_BACKEND_PORT:-8000}"
task_frontend_port="${REAGENT_FRONTEND_PORT:-3000}"

fail() {
  echo "ReAgent V0.1 startup failed: $1" >&2
  exit 1
}

[[ -n "${REAGENT_DATABASE_URL:-}" ]] || fail "export REAGENT_DATABASE_URL for a local PostgreSQL database"
[[ "${task_runtime_dir}" == /* ]] || fail "REAGENT_LOCAL_RUNTIME_DIR must be absolute"
[[ "${task_runtime_dir}" != "${task_repo_root}"* ]] || fail "runtime files must stay outside Git"
[[ "${task_backend_port}" =~ ^[0-9]+$ ]] || fail "REAGENT_BACKEND_PORT must be numeric"
[[ "${task_frontend_port}" =~ ^[0-9]+$ ]] || fail "REAGENT_FRONTEND_PORT must be numeric"

for command_name in conda npm curl lsof; do
  command -v "${command_name}" >/dev/null 2>&1 || fail "${command_name} is required"
done

conda run -n reagent-dev python -c "import fastapi, psycopg, sqlalchemy, uvicorn" \
  >/dev/null 2>&1 || fail "Conda environment reagent-dev is unavailable or incomplete"

conda run -n reagent-dev python -c '
import os
from sqlalchemy.engine import make_url
url = make_url(os.environ["REAGENT_DATABASE_URL"])
if url.get_backend_name() != "postgresql":
    raise SystemExit("database must use PostgreSQL")
if url.host not in {"127.0.0.1", "localhost", "::1"}:
    raise SystemExit("database must be loopback-only")
if (url.database or "").lower() == "projectdb":
    raise SystemExit("ProjectDB is not the V0.1 local product database")
' >/dev/null || fail "REAGENT_DATABASE_URL must select a loopback PostgreSQL database other than ProjectDB"

for task_port in "${task_backend_port}" "${task_frontend_port}"; do
  if lsof -nP -iTCP:"${task_port}" -sTCP:LISTEN >/dev/null 2>&1; then
    fail "port ${task_port} is already in use"
  fi
done

mkdir -p "${task_runtime_dir}"
chmod 700 "${task_runtime_dir}"
for task_process_file in \
  "${task_runtime_dir}/backend.pid" \
  "${task_runtime_dir}/backend.identity" \
  "${task_runtime_dir}/frontend.pid" \
  "${task_runtime_dir}/frontend.identity"; do
  [[ ! -e "${task_process_file}" ]] || fail "stale process record exists; run make stop or inspect the configured runtime directory"
done

cd "${task_repo_root}"
conda run --no-capture-output -n reagent-dev alembic upgrade head
conda run --no-capture-output -n reagent-dev python -c '
import os
from sqlalchemy import text
from backend.database import create_postgres_engine
engine = create_postgres_engine(os.environ["REAGENT_DATABASE_URL"])
try:
    with engine.connect() as connection:
        if connection.scalar(text("SELECT 1")) != 1:
            raise SystemExit("database readiness failed")
finally:
    engine.dispose()
' >/dev/null

task_cleanup_needed=1
cleanup_on_error() {
  if [[ "${task_cleanup_needed}" == "1" ]]; then
    "${task_repo_root}/scripts/dev-stop.sh" >/dev/null 2>&1 || true
  fi
}
trap cleanup_on_error EXIT

env \
  -u REAGENT_OPENALEX_API_KEY \
  REAGENT_DATABASE_URL="${REAGENT_DATABASE_URL}" \
  REAGENT_ARTIFACT_ROOT="${task_runtime_dir}/artifacts" \
  REAGENT_LOCAL_PACKAGE_ROOT="${task_runtime_dir}/local-packages" \
  REAGENT_PAPER_SEARCH_PROVIDER=fake \
  REAGENT_EXPERIMENTAL_FAKE_PROXY_ENABLED=0 \
  REAGENT_EXPERIMENTAL_OPENALEX_PROXY_ENABLED=0 \
  REAGENT_EXPERIMENTAL_OPENALEX_STRUCTURAL_DIAGNOSTICS_ENABLED=0 \
  nohup conda run --no-capture-output -n reagent-dev \
    uvicorn backend.api.app:app --host 127.0.0.1 --port "${task_backend_port}" \
    --no-proxy-headers \
    >"${task_runtime_dir}/backend.log" 2>&1 &
task_backend_pid=$!
printf '%s\n' "${task_backend_pid}" >"${task_runtime_dir}/backend.pid"
ps -p "${task_backend_pid}" -o lstart= >"${task_runtime_dir}/backend.identity" \
  || fail "could not record FastAPI process identity"
chmod 600 "${task_runtime_dir}/backend.pid" "${task_runtime_dir}/backend.identity" "${task_runtime_dir}/backend.log"

for _ in $(seq 1 60); do
  if curl --fail --silent --show-error "http://127.0.0.1:${task_backend_port}/health" >/dev/null 2>&1; then
    break
  fi
  kill -0 "${task_backend_pid}" >/dev/null 2>&1 || fail "FastAPI exited before readiness"
  sleep 0.25
done
curl --fail --silent --show-error "http://127.0.0.1:${task_backend_port}/health" >/dev/null \
  || fail "FastAPI did not become ready"

(
  cd "${task_repo_root}/frontend"
  env REAGENT_API_URL="http://127.0.0.1:${task_backend_port}" \
    nohup npm run dev -- --hostname 127.0.0.1 --port "${task_frontend_port}" \
    >"${task_runtime_dir}/frontend.log" 2>&1
) &
task_frontend_pid=$!
printf '%s\n' "${task_frontend_pid}" >"${task_runtime_dir}/frontend.pid"
ps -p "${task_frontend_pid}" -o lstart= >"${task_runtime_dir}/frontend.identity" \
  || fail "could not record Next.js process identity"
chmod 600 "${task_runtime_dir}/frontend.pid" "${task_runtime_dir}/frontend.identity" "${task_runtime_dir}/frontend.log"

for _ in $(seq 1 120); do
  if curl --fail --silent --show-error "http://127.0.0.1:${task_frontend_port}/projects" >/dev/null 2>&1; then
    break
  fi
  kill -0 "${task_frontend_pid}" >/dev/null 2>&1 || fail "Next.js exited before readiness"
  sleep 0.25
done
curl --fail --silent --show-error "http://127.0.0.1:${task_frontend_port}/projects" >/dev/null \
  || fail "Next.js did not become ready"

task_cleanup_needed=0
echo "ReAgent V0.1 local product is ready."
echo "Frontend: http://127.0.0.1:${task_frontend_port}/projects"
echo "Backend:  http://127.0.0.1:${task_backend_port}/health"
echo "Runtime logs and PIDs: ${task_runtime_dir}"
echo "Stop only these application processes with: make stop"
