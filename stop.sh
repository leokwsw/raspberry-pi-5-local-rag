#!/bin/bash
# Stop script for Raspberry Pi 5 Local RAG
# Uses PM2 for process management

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

APP_NAME="rag"
STOP_OLLAMA=false
DELETE_PROCESS=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --all)
            STOP_OLLAMA=true
            shift
            ;;
        --delete)
            DELETE_PROCESS=true
            shift
            ;;
        --name)
            APP_NAME="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: ./stop.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --all          Stop RAG and Ollama service"
            echo "  --delete       Delete process from PM2 (not just stop)"
            echo "  --name NAME    PM2 process name (default: rag)"
            echo "  -h, --help     Show this help message"
            echo ""
            echo "Examples:"
            echo "  ./stop.sh                # Stop RAG application"
            echo "  ./stop.sh --all          # Stop RAG and Ollama"
            echo "  ./stop.sh --delete       # Stop and remove from PM2"
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
echo "  Stopping Raspberry Pi 5 Local RAG"
echo "=========================================="
echo ""

STOPPED=false

# Stop PM2 process
if command -v pm2 &> /dev/null; then
    if pm2 describe "$APP_NAME" &> /dev/null; then
        echo -e "${YELLOW}Stopping PM2 process '$APP_NAME'...${NC}"
        if [ "$DELETE_PROCESS" = true ]; then
            pm2 delete "$APP_NAME"
            echo -e "${GREEN}✓ Process deleted from PM2${NC}"
        else
            pm2 stop "$APP_NAME"
            echo -e "${GREEN}✓ Process stopped${NC}"
        fi
        pm2 save 2>/dev/null || true
        STOPPED=true
    else
        echo -e "${YELLOW}PM2 process '$APP_NAME' not found${NC}"
    fi
fi

# Also check for any running Python processes (non-PM2)
echo ""
echo -e "${YELLOW}Checking for other running processes...${NC}"

# Stop web_gui.py
WEB_PIDS=$(pgrep -f "python.*web_gui.py" 2>/dev/null || true)
if [ -n "$WEB_PIDS" ]; then
    echo -e "  Stopping web_gui.py processes..."
    for pid in $WEB_PIDS; do
        kill "$pid" 2>/dev/null && echo -e "  ${GREEN}✓ Stopped PID $pid${NC}"
    done
    STOPPED=true
fi

# Stop app_gradio.py
GRADIO_PIDS=$(pgrep -f "python.*app_gradio.py" 2>/dev/null || true)
if [ -n "$GRADIO_PIDS" ]; then
    echo -e "  Stopping app_gradio.py processes..."
    for pid in $GRADIO_PIDS; do
        kill "$pid" 2>/dev/null && echo -e "  ${GREEN}✓ Stopped PID $pid${NC}"
    done
    STOPPED=true
fi

# Stop app.py (CLI)
CLI_PIDS=$(pgrep -f "python.*app.py" 2>/dev/null || true)
if [ -n "$CLI_PIDS" ]; then
    echo -e "  Stopping app.py processes..."
    for pid in $CLI_PIDS; do
        kill "$pid" 2>/dev/null && echo -e "  ${GREEN}✓ Stopped PID $pid${NC}"
    done
    STOPPED=true
fi

# Stop Ollama if requested
if [ "$STOP_OLLAMA" = true ]; then
    echo ""
    echo -e "${YELLOW}Stopping Ollama service...${NC}"
    pkill -f "ollama serve" 2>/dev/null && echo -e "${GREEN}✓ Ollama stopped${NC}" || echo -e "${YELLOW}Ollama was not running${NC}"
    STOPPED=true
fi

echo ""
if [ "$STOPPED" = true ]; then
    echo -e "${GREEN}All processes stopped.${NC}"
else
    echo -e "${YELLOW}No running RAG processes found.${NC}"
fi

echo ""
echo "Usage:"
echo "  ./stop.sh            # Stop RAG application"
echo "  ./stop.sh --all      # Stop RAG and Ollama service"
echo "  ./stop.sh --delete   # Stop and remove from PM2"
echo ""

# Show PM2 status if available
if command -v pm2 &> /dev/null; then
    echo "Current PM2 status:"
    pm2 list
fi
