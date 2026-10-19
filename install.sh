#!/usr/bin/env bash
# EquestrianFence setup: install the test runner and the console script, then EXIT.
# It never starts a server and never touches system packages.
set -euo pipefail
cd "$(dirname "$0")"

PYTHON="${PYTHON:-python3}"

echo "==> Upgrading pip / setuptools / wheel"
"$PYTHON" -m pip install --upgrade pip setuptools wheel

echo "==> Installing the test runner (requirements.txt)"
"$PYTHON" -m pip install -r requirements.txt

echo "==> Installing the equestrianfence console script"
"$PYTHON" -m pip install -e .

echo "==> Self-check"
"$PYTHON" -c 'import equestrian_fence; print("module import OK", equestrian_fence.__version__)'
"$PYTHON" equestrian_fence.py layout --length 100 --width 50 --spacing 10 > /dev/null
echo "layout OK"

echo
echo "Setup complete."
echo "Run:  python3 equestrian_fence.py --help      (or: equestrianfence --help)"
echo "Demo: bash demo.sh"
echo "Test: python3 -m pytest -q"
