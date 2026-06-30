#!/bin/bash
# Stop script for Raspberry Pi 5 Local RAG
# Stops running RAG processes

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================="
echo "  Stopping Raspberry Pi 5 Local RAG"
echo "=========================================="
echo ""

STOPPED=false

# Stop by PID file
if [ -f ".rag_pid" ]; then
    PID=$(cat .rag_pid)
    if ps -p "$PID" > /dev/null 2>&1; then
        echo -e "${YELLOW}Stopping RAG process (PID: $PID)...${NC}"
        kill "$PID" 2>/dev/null
        sleep 2
        if ps -p "$PID" > /dev/null 2>&1; then
            kill -9 "$PID" 2>/dev/null
        fi
        echo -e "${GREEN}✓ RAG process stopped${NC}"
        STOPPED=true
    fi
    rm -f .rag_pid
fi

# Find and stop any running Python processes for this project
echo -e "${YELLOW}Checking for running processes...${NC}"

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

# Option to stop Ollama
if [[ "$1" == "--all" ]]; then
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
echo "  ./stop.sh        # Stop RAG application only"
echo "  ./stop.sh --all  # Stop RAG and Ollama service"
echo ""
