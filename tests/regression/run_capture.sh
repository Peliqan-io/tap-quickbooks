#!/usr/bin/env bash
# Run baseline capture inside a Python 3.9 container.
# Usage: bash run_capture.sh

set -euo pipefail

TAP_DIR="$(cd "$(dirname "$0")/../.." && pwd)"

echo "==> Running baseline capture in python:3.9-slim"
echo "    Tap dir: $TAP_DIR"

docker run --rm \
  -v "$TAP_DIR":/tap \
  -w /tap \
  -e TAP_QUICKBOOKS_CLIENT_ID="${TAP_QUICKBOOKS_CLIENT_ID:?}" \
  -e TAP_QUICKBOOKS_CLIENT_SECRET="${TAP_QUICKBOOKS_CLIENT_SECRET:?}" \
  -e TAP_QUICKBOOKS_REFRESH_TOKEN="${TAP_QUICKBOOKS_REFRESH_TOKEN:?}" \
  -e TAP_QUICKBOOKS_ACCESS_TOKEN="${TAP_QUICKBOOKS_ACCESS_TOKEN:?}" \
  -e TAP_QUICKBOOKS_REALM_ID="${TAP_QUICKBOOKS_REALM_ID:?}" \
  -e TAP_QUICKBOOKS_SANDBOX="${TAP_QUICKBOOKS_SANDBOX:-false}" \
  -e TAP_QUICKBOOKS_INCLUDE_STREAMS="${TAP_QUICKBOOKS_INCLUDE_STREAMS:-accounts}" \
  -e TAP_QUICKBOOKS_START_DATE="${TAP_QUICKBOOKS_START_DATE:-2024-01-01T00:00:00Z}" \
  -e AES_SECRET_KEY="peliqan-test-key" \
  python:3.9-slim \
  bash -c "
    apt-get update -qq && apt-get install -y -qq git > /dev/null
    python -m venv /venv
    /venv/bin/pip install -e . -q
    /venv/bin/python tests/regression/capture.py
  "

echo ""
echo "==> Baseline written to tests/regression/baseline/"
