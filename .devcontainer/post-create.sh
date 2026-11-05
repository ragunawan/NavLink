#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

# Docker creates these named volumes as root. Only change their ownership.
sudo chown -R "$(id -u):$(id -g)" .venv frontend/node_modules /var/lib/navylink

# Fail early if the Python build cannot support the application's search index.
python -c 'import sqlite3; sqlite3.connect(":memory:").execute("CREATE VIRTUAL TABLE check_fts USING fts5(content)")'

# Creates .env only if missing; seeds only an empty development database.
make setup

# Match Chromium to the Playwright version installed from package-lock.json.
(
  cd frontend
  npx playwright install --with-deps chromium
)
