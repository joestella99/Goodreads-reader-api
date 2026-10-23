#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ ! -f .env ]]; then bash scripts/bootstrap.sh; fi
set -a
source .env
set +a
if ! python3 -c 'import fastapi, uvicorn, multipart' >/dev/null 2>&1; then
  python3 -m pip install -r requirements.txt
fi
echo "API running at http://127.0.0.1:8000 (keep forwarded port Private)"
echo "API documentation: http://127.0.0.1:8000/docs"
python3 -m uvicorn app:app --host 0.0.0.0 --port 8000
