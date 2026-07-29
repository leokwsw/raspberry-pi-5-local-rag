#!/usr/bin/env bash
set -euo pipefail
install_root="${INSTALL_ROOT:-/opt/pi-local-rag}"
data_root="${DATA_ROOT:-/var/lib/pi-local-rag}"
if [[ ! -f apps/web/dist/index.html ]]; then
  if ! command -v npm >/dev/null 2>&1; then
    echo "apps/web/dist is missing; build the web release with npm before installing" >&2
    exit 1
  fi
  npm --prefix apps/web ci
  npm --prefix apps/web run build
fi
if ! getent passwd rag >/dev/null; then
  sudo useradd --system --home-dir "$data_root" --shell /usr/sbin/nologin rag
fi
sudo install -d -o rag -g rag "$install_root" "$data_root"
sudo rsync -a --delete --exclude .git --exclude .venv ./ "$install_root/"
sudo python3 -m venv "$install_root/.venv"
sudo "$install_root/.venv/bin/pip" install "$install_root[pdf]"
sudo install -m 0644 deploy/systemd/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable llama-server embedding-server rag-api rag-worker
