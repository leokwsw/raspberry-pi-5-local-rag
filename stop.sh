#!/usr/bin/env bash

set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

REMOVE_ORPHANS=true

usage() {
    cat <<'EOF'
Usage: ./stop.sh [OPTIONS]

Stop the Local RAG Docker Compose stack. Persistent volumes and host Ollama
are always preserved.

Options:
  --keep-orphans    Do not remove containers no longer defined by Compose
  -h, --help        Show this help message
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --keep-orphans)
            REMOVE_ORPHANS=false
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Error: unknown option: $1" >&2
            usage >&2
            exit 2
            ;;
    esac
    shift
done

if docker compose version >/dev/null 2>&1; then
    COMPOSE=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
    COMPOSE=(docker-compose)
else
    echo "Error: Docker Compose is not installed." >&2
    exit 1
fi

if ! docker info >/dev/null 2>&1; then
    echo "Error: cannot connect to the Docker daemon." >&2
    exit 1
fi

DOWN_ARGS=(down)
if [[ "$REMOVE_ORPHANS" == true ]]; then
    DOWN_ARGS+=(--remove-orphans)
fi

echo "Stopping Local RAG services..."
"${COMPOSE[@]}" "${DOWN_ARGS[@]}"

echo
echo "All Local RAG containers and networks have stopped."
echo "Persistent volumes and the host Ollama service were preserved."
echo "Start again with: ./start.sh"
