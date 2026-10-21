#!/usr/bin/env bash
# Bootstrap the local model gateway. Safe to re-run: every step checks before it acts.
#
#   1. Ollama installed (Homebrew)
#   2. Ollama server running with the memory settings this Mac needs
#   3. Every Ollama model named in litellm_config.yaml pulled (and only those)
#   4. The pinned Python environment installed from uv.lock
set -euo pipefail

cd "$(dirname "$0")"

# Keep a copy of every run's output (logs/ is git-ignored), so it can be checked afterwards.
# Re-run once through a pipe to tee: process substitution needs /dev/fd, which Claude's sandbox blocks.
if [ -z "${SETUP_SH_LOGGING:-}" ]; then
  mkdir -p logs
  SETUP_SH_LOGGING=1 bash "$0" "$@" 2>&1 | tee -a logs/setup.log
  exit "${PIPESTATUS[0]}"
fi
echo "=== setup.sh $(date '+%Y-%m-%d %H:%M:%S')"

OLLAMA_URL="http://127.0.0.1:11434"
# One model resident at a time and a 4096-token context window: what fits in 18 GB.
SERVER_ENV=(OLLAMA_MAX_LOADED_MODELS=1 OLLAMA_CONTEXT_LENGTH=4096)

step() { printf '\n== %s\n' "$1"; }
ok() { printf '   ok: %s\n' "$1"; }

server_up() { curl -sf -m 3 "$OLLAMA_URL/api/version" >/dev/null 2>&1; }

brew_install() {
  if ! command -v brew >/dev/null 2>&1; then
    echo "Homebrew is required to install $1: https://brew.sh" >&2
    exit 1
  fi
  brew install "$1"
}

step "Ollama installed"
if command -v ollama >/dev/null 2>&1; then
  ok "$(ollama --version 2>/dev/null | tail -1)"
else
  brew_install ollama
fi

step "Ollama server running"
if server_up; then
  ok "already running at $OLLAMA_URL"
  echo "   note: can't read a running server's settings; if you started it yourself, make sure"
  echo "         it was with: ${SERVER_ENV[*]} ollama serve"
else
  env "${SERVER_ENV[@]}" nohup ollama serve >logs/ollama.log 2>&1 &
  for _ in $(seq 1 30); do
    server_up && break
    sleep 1
  done
  server_up || { echo "Ollama didn't start; see logs/ollama.log" >&2; exit 1; }
  ok "started in the background (${SERVER_ENV[*]}), log: logs/ollama.log"
fi

step "Models named in litellm_config.yaml"
models=$(sed -En 's#^[[:space:]]*model:[[:space:]]*ollama(_chat)?/([^[:space:]]+).*#\2#p' litellm_config.yaml | sort -u)
if [ -z "$models" ]; then
  echo "   no ollama/ or ollama_chat/ models in litellm_config.yaml; nothing to pull"
fi
for model in $models; do
  # `ollama list` shows an untagged model as name:latest.
  case "$model" in *:*) tagged="$model" ;; *) tagged="${model}:latest" ;; esac
  if ollama list | awk 'NR > 1 {print $1}' | grep -qxF "$tagged"; then
    ok "$model already pulled"
  else
    ollama pull "$model"
  fi
done

step "Pinned Python environment"
if ! command -v uv >/dev/null 2>&1; then
  brew_install uv
fi
uv sync --frozen
# Read the version from package metadata: importing litellm would fetch a cost map from GitHub.
ok "installed from uv.lock (litellm $(uv run --frozen python -c 'import importlib.metadata as m; print(m.version("litellm"))'))"

printf '\nDone. Start the gateway with ./run_proxy.sh, then run the validator skill.\n'
