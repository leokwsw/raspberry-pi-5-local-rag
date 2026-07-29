#!/usr/bin/env bash
set -euo pipefail
install_root="${INSTALL_ROOT:-/opt/pi-local-rag}"
data_root="${DATA_ROOT:-/var/lib/pi-local-rag}"
sudo install -d -o rag -g rag "$install_root" "$data_root"
sudo rsync -a --delete --exclude .git --exclude .venv ./ "$install_root/"
sudo python3 -m venv "$install_root/.venv"
sudo "$install_root/.venv/bin/pip" install "$install_root[pdf]"
sudo install -m 0644 deploy/systemd/rag-*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable rag-api rag-worker
