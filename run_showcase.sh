#!/usr/bin/env bash
set -euo pipefail

if [ ! -d .venv ]; then
  python -m venv .venv
fi
source .venv/bin/activate
pip install -e .
python demo_app.py
