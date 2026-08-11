#!/usr/bin/env bash
set -euo pipefail

exec env \
  -u REAGENT_OPENALEX_API_KEY \
  -u OPENALEX_API_KEY \
  -u OPENAI_API_KEY \
  -u ANTHROPIC_API_KEY \
  -u REAGENT_PROXY_TOKEN \
  -u REAGENT_LOCAL_SESSION_TOKEN \
  "$@"
