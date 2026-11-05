#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

api_ready() {
  .venv/bin/python -c 'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8000/api/health", timeout=1)' >/dev/null 2>&1
}

if api_ready; then
  echo "NavyLINK is already running at http://127.0.0.1:8000"
  exit 0
fi

nohup make run >/tmp/navylink.log 2>&1 </dev/null &
server_pid=$!

for _ in {1..30}; do
  if api_ready; then
    echo "NavyLINK started at http://127.0.0.1:8000"
    exit 0
  fi
  if ! kill -0 "$server_pid" 2>/dev/null; then
    echo "NavyLINK failed to start; startup log follows:" >&2
    cat /tmp/navylink.log >&2
    exit 1
  fi
  sleep 1
done

echo "NavyLINK did not become ready; startup log follows:" >&2
cat /tmp/navylink.log >&2
exit 1
