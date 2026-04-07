#!/usr/bin/env bash
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"

# ── Load .env if present ───────────────────────────────────────────────────────
if [ -f "$ROOT/.env" ]; then
  set -a
  source "$ROOT/.env"
  set +a
  echo "Loaded .env"
fi

# ── Backend ────────────────────────────────────────────────────────────────────
echo "Starting backend on http://localhost:8000 ..."
(
  cd "$ROOT/backend"
  source venv/bin/activate
  uvicorn main:app --reload --port 8000
) &
BACKEND_PID=$!

# ── Frontend ───────────────────────────────────────────────────────────────────
echo "Starting frontend on http://localhost:5173 ..."
(
  cd "$ROOT/frontend"
  pnpm dev
) &
FRONTEND_PID=$!

echo ""
echo "  Backend  → http://localhost:8000"
echo "  Frontend → http://localhost:5173"
echo "  API docs → http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop both servers."

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT TERM
wait
