#!/usr/bin/env sh
set -eu

if [ -z "${PARITOK_API_KEY:-}" ]; then
  echo "PARITOK_API_KEY is missing. Inject it as a runtime environment variable." >&2
  exit 1
fi

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_ROOT=$(dirname -- "$SCRIPT_DIR")

exec paritok proxy \
  --host 127.0.0.1 \
  --port 8080 \
  --config-file "$PROJECT_ROOT/paritok.yaml" \
  --openai-url "https://api.deepseek.com/chat/completions" \
  --log-level info
