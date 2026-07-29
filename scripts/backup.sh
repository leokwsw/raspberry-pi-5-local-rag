#!/usr/bin/env bash
set -euo pipefail
source_path="${RAG_DATA_DIR:-/var/lib/pi-local-rag}"
destination="${1:?usage: backup.sh DESTINATION.tar.gz}"
tar -C "$source_path" -czf "$destination" .
