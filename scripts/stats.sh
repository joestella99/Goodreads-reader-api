#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
set -a
source .env
set +a
curl -fsS "http://127.0.0.1:8000/stats" -H "X-API-Key: $READING_API_KEY"
printf '\n'
