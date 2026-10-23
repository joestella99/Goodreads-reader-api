#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ ! -f .env ]]; then
  python3 - <<'PY'
import secrets
from pathlib import Path
Path(".env").write_text("READING_API_KEY=" + secrets.token_urlsafe(32) + "\nGOODREADS_USER_ID=167934914\n")
print("Created a local .env file with a random private API key and the account's Goodreads ID.")
PY
fi
echo "Ready. Run: bash scripts/start.sh"
