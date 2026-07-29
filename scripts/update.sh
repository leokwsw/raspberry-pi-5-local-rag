#!/usr/bin/env bash
set -euo pipefail
git pull --ff-only
.venv/bin/pip install -e '.[pdf]'
sudo systemctl restart rag-api rag-worker
