#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ ! -f .env ]]; then
  echo "Run bash scripts/bootstrap.sh first" >&2
  exit 1
fi
set -a
source .env
set +a
curl -fsS -X POST "http://127.0.0.1:8000/sync/goodreads" -H "X-API-Key: $READING_API_KEY"
printf '\n'
