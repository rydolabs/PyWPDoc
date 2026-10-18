#!/usr/bin/env bash
# PyWPDoc tests only. No Git operations or uploads.
set -euo pipefail
cd "$(dirname "$0")"
if [[ ! -f .venv/bin/python ]]; then
  python3 -m venv .venv
fi
.venv/bin/python -m pip install -e '.[test,unified]'
.venv/bin/python scripts/run_local_qa.py
