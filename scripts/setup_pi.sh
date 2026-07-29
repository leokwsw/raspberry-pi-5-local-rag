#!/usr/bin/env bash
set -euo pipefail
sudo apt-get update
sudo apt-get install -y build-essential cmake git libopenblas-dev python3-venv
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -e '.[pdf,test]'
echo "Pi environment ready"
