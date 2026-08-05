#!/usr/bin/env bash
set -euo pipefail

task_runtime_dir="${REAGENT_LOCAL_RUNTIME_DIR:-/tmp/reagent-v0-1-${UID}}"

stop_tree() {
  local task_pid="$1"
  local task_child
  while read -r task_child; do
    [[ -n "${task_child}" ]] && stop_tree "${task_child}"
  done < <(pgrep -P "${task_pid}" 2>/dev/null || true)
  kill "${task_pid}" 2>/dev/null || true
}

task_pid_list=""
for task_name in frontend backend; do
  task_pid_file="${task_runtime_dir}/${task_name}.pid"
  task_identity_file="${task_runtime_dir}/${task_name}.identity"
  [[ -f "${task_pid_file}" ]] || continue
  task_pid="$(tr -d '[:space:]' <"${task_pid_file}")"
  if [[ "${task_pid}" =~ ^[0-9]+$ ]] && kill -0 "${task_pid}" >/dev/null 2>&1; then
    [[ -f "${task_identity_file}" ]] || {
      echo "Refusing to stop ${task_name}: process identity record is missing." >&2
      exit 1
    }
    task_expected_identity="$(<"${task_identity_file}")"
    task_current_identity="$(ps -p "${task_pid}" -o lstart= 2>/dev/null || true)"
    [[ -n "${task_current_identity}" && "${task_current_identity}" == "${task_expected_identity}" ]] || {
      echo "Refusing to stop ${task_name}: PID identity no longer matches." >&2
      exit 1
    }
    task_pid_list="${task_pid_list} ${task_pid}"
    stop_tree "${task_pid}"
  else
    rm -f "${task_pid_file}" "${task_identity_file}"
  fi
done

for _ in $(seq 1 40); do
  task_running=0
  for task_pid in ${task_pid_list}; do
    if kill -0 "${task_pid}" >/dev/null 2>&1; then task_running=1; fi
  done
  [[ "${task_running}" == "0" ]] && break
  sleep 0.1
done

for task_pid in ${task_pid_list}; do
  if kill -0 "${task_pid}" >/dev/null 2>&1; then
    kill -9 "${task_pid}" 2>/dev/null || true
  fi
done
rm -f \
  "${task_runtime_dir}/frontend.pid" \
  "${task_runtime_dir}/frontend.identity" \
  "${task_runtime_dir}/backend.pid" \
  "${task_runtime_dir}/backend.identity"

echo "Stopped ReAgent V0.1 application processes. PostgreSQL was not stopped or modified."
