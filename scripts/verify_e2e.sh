#!/bin/bash

set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "==> Running frontend quality checks"
npm --prefix "$ROOT_DIR/frontend" run lint
npm --prefix "$ROOT_DIR/frontend" run build

echo "==> Running backend smoke tests"
cd "$ROOT_DIR/backend"
PYTHONPATH=. pytest app/tests/test_sandbox_service.py -q
PYTHONPATH=. pytest app/tests/test_finance_research_adapter.py -q

echo "==> End-to-end verification checks passed"
