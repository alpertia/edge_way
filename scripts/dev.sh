#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -q -r requirements.txt
EDGEWAY_ENV="${EDGEWAY_ENV:-./dev.env}" exec .venv/bin/uvicorn edgeway.api.main:app --reload --port 8080
