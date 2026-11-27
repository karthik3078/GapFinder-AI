#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then
  echo 'Create .venv and install requirements first. See README.md.' >&2
  exit 1
fi
if [ ! -f frontend/dist/index.html ]; then
  (cd frontend && npm ci && npm run build)
fi
echo 'Open http://127.0.0.1:8000 - Demo: student@demo.com / demo123'
exec .venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
