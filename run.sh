#!/bin/bash
# Run script for Raspberry Pi 5 Local RAG
# Starts the enhanced Web GUI

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Default values
HOST="0.0.0.0"
PORT="7860"
MODE="web"  # web, cli, or basic

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --host)
            HOST="$2"
            shift 2
            ;;
        --port)
            PORT="$2"
            shift 2
            ;;
        --cli)
            MODE="cli"
            shift
            ;;
        --basic)
            MODE="basic"
            shift
            ;;
        --help|-h)
            echo "Usage: ./run.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --host HOST    Server host (default: 0.0.0.0)"
            echo "  --port PORT    Server port (default: 7860)"
            echo "  --cli          Run CLI mode instead of Web GUI"
            echo "  --basic        Run basic Gradio GUI instead of enhanced"
            echo "  -h, --help     Show this help message"
            echo ""
            echo "Examples:"
            echo "  ./run.sh                    # Start enhanced Web GUI on port 7860"
            echo "  ./run.sh --port 8080        # Start on port 8080"
            echo "  ./run.sh --cli              # Start CLI mode"
            echo "  ./run.sh --basic            # Start basic Gradio GUI"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo "=========================================="
echo "  Raspberry Pi 5 Local RAG"
echo "=========================================="
echo ""

# Check virtual environment
if [ ! -d ".venv" ]; then
    echo -e "${RED}Virtual environment not found.${NC}"
    echo "Please run ./setup.sh first."
    exit 1
fi

# Activate virtual environment
source .venv/bin/activate

# Check if Ollama is running
echo -e "${YELLOW}Checking Ollama service...${NC}"
if ! ollama list &> /dev/null; then
    echo -e "${YELLOW}Starting Ollama service...${NC}"
    ollama serve &> /dev/null &
    sleep 3
fi
echo -e "${GREEN}✓ Ollama is running${NC}"
echo ""

# Save PID file for stop script
echo $$ > .rag_pid

# Run the appropriate mode
case $MODE in
    web)
        echo -e "${GREEN}Starting Enhanced Web GUI...${NC}"
        echo "  URL: http://$HOST:$PORT"
        echo "  Press Ctrl+C to stop"
        echo ""
        python3 web_gui.py --host "$HOST" --port "$PORT"
        ;;
    basic)
        echo -e "${GREEN}Starting Basic Web GUI...${NC}"
        echo "  URL: http://$HOST:$PORT"
        echo "  Press Ctrl+C to stop"
        echo ""
        python3 app_gradio.py --host "$HOST" --port "$PORT"
        ;;
    cli)
        echo -e "${GREEN}Starting CLI Mode...${NC}"
        echo "  Type 'exit' to quit"
        echo ""
        python3 app.py --stream
        ;;
esac

# Cleanup PID file
rm -f .rag_pid
