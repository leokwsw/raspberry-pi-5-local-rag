#!/usr/bin/env bash

set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

BUILD=true
PULL=false
WAIT=true
CHECK_OLLAMA=true

usage() {
    cat <<'EOF'
Usage: ./start.sh [OPTIONS]

Start the Local RAG Docker Compose stack.

Options:
  --no-build             Start with existing images without rebuilding
  --pull                 Pull newer base images before starting
  --no-wait              Do not wait for the Local RAG API to become ready
  --skip-ollama-check    Skip the host Ollama availability check
  -h, --help             Show this help message

Examples:
  ./start.sh
  ./start.sh --no-build
  ./start.sh --pull
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --no-build)
            BUILD=false
            ;;
        --pull)
            PULL=true
            ;;
        --no-wait)
            WAIT=false
            ;;
        --skip-ollama-check)
            CHECK_OLLAMA=false
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
    echo "Warning: Docker Compose V1 is deprecated; Compose V2 is recommended."
else
    echo "Error: Docker Compose is not installed." >&2
    echo "Install Docker Engine and the Docker Compose plugin first." >&2
    exit 1
fi

if ! docker info >/dev/null 2>&1; then
    echo "Error: cannot connect to the Docker daemon." >&2
    echo "Start Docker, or add the current user to the docker group and sign in again." >&2
    exit 1
fi

if [[ ! -f .env ]]; then
    echo "Error: .env does not exist." >&2
    echo "Run: cp .env.example .env" >&2
    echo "Then set a strong ARANGODB_PASSWORD before starting." >&2
    exit 1
fi

ARANGO_PASSWORD_LINE="$(grep -E '^[[:space:]]*ARANGODB_PASSWORD=' .env | tail -n 1 || true)"
ARANGO_PASSWORD="${ARANGO_PASSWORD_LINE#*=}"
ARANGO_PASSWORD="${ARANGO_PASSWORD%$'\r'}"
if [[ -z "${ARANGO_PASSWORD//[[:space:]\"\']/}" ]]; then
    echo "Error: ARANGODB_PASSWORD in .env must not be empty." >&2
    exit 1
fi

if [[ "$CHECK_OLLAMA" == true ]]; then
    if ! command -v curl >/dev/null 2>&1; then
        echo "Error: curl is required for the Ollama and health checks." >&2
        exit 1
    fi
    OLLAMA_URL="$(grep -E '^[[:space:]]*OLLAMA_BASE_URL=' .env | tail -n 1 | cut -d= -f2- || true)"
    OLLAMA_URL="${OLLAMA_URL:-http://host.docker.internal:11434}"
    OLLAMA_CHECK_URL="${OLLAMA_URL/host.docker.internal/127.0.0.1}"
    if ! curl -fsS --max-time 5 "${OLLAMA_CHECK_URL%/}/api/tags" >/dev/null; then
        echo "Error: Ollama is not reachable at ${OLLAMA_CHECK_URL}." >&2
        echo "Start Ollama and ensure it listens on 0.0.0.0:11434." >&2
        echo "For a deliberately remote Ollama endpoint, use --skip-ollama-check." >&2
        exit 1
    fi
    echo "✓ Ollama is reachable"
fi

echo "✓ Docker is ready"

if [[ "$PULL" == true ]]; then
    echo "Pulling service images..."
    "${COMPOSE[@]}" pull
fi

UP_ARGS=(up -d)
if [[ "$BUILD" == true ]]; then
    UP_ARGS+=(--build)
fi

echo "Starting Local RAG services..."
"${COMPOSE[@]}" "${UP_ARGS[@]}"

if [[ "$WAIT" == true ]]; then
    if ! command -v curl >/dev/null 2>&1; then
        echo "Warning: curl is unavailable; skipping API readiness check."
    else
        echo "Waiting for the API to become ready..."
        READY=false
        for _ in {1..240}; do
            if curl -fsS --max-time 3 http://localhost:3000/api/health 2>/dev/null | grep -q '"status":"ok"'; then
                READY=true
                break
            fi
            sleep 5
        done
        if [[ "$READY" != true ]]; then
            echo "Error: services started, but the API did not become ready within 20 minutes." >&2
            echo "Inspect logs with: ${COMPOSE[*]} logs --tail=200 backend reranker-service" >&2
            exit 1
        fi
    fi
fi

echo
echo "Local RAG is running."
echo "  Web UI:          http://localhost:3000"
echo "  Backend API:     http://localhost:8080"
echo "  API docs:        http://localhost:8080/docs"
echo "  Qdrant:          http://localhost:6333"
echo "  Reranker:        http://localhost:8081/health"
echo "  Chunking service:http://localhost:8082/health"
echo
echo "Commands:"
echo "  View status: ${COMPOSE[*]} ps"
echo "  Follow logs: ${COMPOSE[*]} logs -f"
echo "  Stop safely: ./stop.sh"
