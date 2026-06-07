#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

(
  cd "$ROOT_DIR/backend"
  python run.py
) &
BACKEND_PID=$!

(
  cd "$ROOT_DIR/web"
  pnpm dev
) &
WEB_PID=$!

cleanup() {
  kill "$BACKEND_PID" "$WEB_PID" 2>/dev/null || true
}

trap cleanup EXIT INT TERM
wait
