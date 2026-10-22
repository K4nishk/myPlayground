#!/usr/bin/env bash
# Start the LiteLLM gateway on 127.0.0.1:4000 in the foreground (Ctrl-C to stop).
#
# Fixed to loopback and port 4000: the validator and every client expect it there, and binding
# to another interface would expose the gateway to the network.
#
# Logs go to the terminal and to logs/proxy.log, which the validator skill reads when it
# diagnoses a failure.
set -euo pipefail

cd "$(dirname "$0")"

# A non-secret local default; set your own in the environment to override it.
export LITELLM_MASTER_KEY="${LITELLM_MASTER_KEY:-sk-local-dev}"
# Use the cost map bundled with the pinned release instead of fetching one from GitHub.
export LITELLM_LOCAL_MODEL_COST_MAP=True
# Stop LiteLLM loading a .env by itself. In its default DEV mode it searches upward from its install
# folder, reaches problem_first_ai/.env, and loads every credential in it.
export LITELLM_MODE=PRODUCTION

if ! command -v uv >/dev/null 2>&1; then
  echo "uv is not installed. Run ./setup.sh first." >&2
  exit 1
fi

# Frontier aliases read OPENROUTER_API_KEY. Unless it's already exported, take that one variable,
# and nothing else, from the course's .env (GATEWAY_ENV_FILE overrides the path). Never printed.
env_file="${GATEWAY_ENV_FILE:-../.env}"
if [ -z "${OPENROUTER_API_KEY:-}" ] && [ -f "$env_file" ]; then
  OPENROUTER_API_KEY="$(uv run --frozen python -I -c \
    'import sys; from dotenv import dotenv_values; print(dotenv_values(sys.argv[1]).get("OPENROUTER_API_KEY") or "")' \
    "$env_file")"
  export OPENROUTER_API_KEY
fi
key_warning=""
if [ -z "${OPENROUTER_API_KEY:-}" ]; then
  key_warning="WARNING: OPENROUTER_API_KEY is neither exported nor in $env_file, so frontier aliases will fail."
fi

if (exec 3<>/dev/tcp/127.0.0.1/4000) 2>/dev/null; then
  echo "Port 4000 on 127.0.0.1 is already in use; is the gateway already running?" >&2
  exit 1
fi

mkdir -p logs
echo "Starting LiteLLM gateway on http://127.0.0.1:4000 (config: litellm_config.yaml)"
# The key warning goes through tee with the gateway's output, so it lands in logs/proxy.log too.
{
  if [ -n "$key_warning" ]; then echo "$key_warning"; fi
  uv run --frozen litellm --config litellm_config.yaml --host 127.0.0.1 --port 4000
} 2>&1 | tee logs/proxy.log
