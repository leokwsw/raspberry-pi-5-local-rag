#!/usr/bin/env bash
set -euo pipefail
archive="${1:?usage: restore.sh BACKUP.tar.gz}"
destination="${RAG_DATA_DIR:-/var/lib/pi-local-rag}"
mkdir -p "$destination"
tar -C "$destination" -xzf "$archive"
