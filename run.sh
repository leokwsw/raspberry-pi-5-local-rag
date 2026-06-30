#!/bin/bash
# Run script for Raspberry Pi 5 Local RAG
# Uses PM2 for process management

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Default values
HOST="0.0.0.0"
PORT="7860"
MODE="web"
APP_NAME="rag"
NO_PM2=false

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
        --name)
            APP_NAME="$2"
            shift 2
            ;;
        --no-pm2)
            NO_PM2=true
            shift
            ;;
        --help|-h)
            echo "Usage: ./run.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --host HOST    Server host (default: 0.0.0.0)"
            echo "  --port PORT    Server port (default: 7860)"
            echo "  --cli          Run CLI mode (foreground only)"
            echo "  --basic        Run basic Gradio GUI instead of enhanced"
            echo "  --name NAME    PM2 process name (default: rag)"
            echo "  --no-pm2       Run without PM2 (foreground mode)"
            echo "  -h, --help     Show this help message"
            echo ""
            echo "Examples:"
            echo "  ./run.sh                    # Start with PM2 on port 7860"
            echo "  ./run.sh --port 8080        # Start on port 8080"
            echo "  ./run.sh --no-pm2           # Run in foreground (no PM2)"
            echo "  ./run.sh --cli              # Start CLI mode"
            echo ""
            echo "PM2 Commands:"
            echo "  pm2 logs rag                # View logs"
            echo "  pm2 monit                   # Monitor dashboard"
            echo "  pm2 restart rag             # Restart application"
            echo "  pm2 save                    # Save process list"
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

# Get absolute path to Python
PYTHON_PATH="$SCRIPT_DIR/.venv/bin/python3"

# Check if Ollama is running
echo -e "${YELLOW}Checking Ollama service...${NC}"
if ! ollama list &> /dev/null; then
    echo -e "${YELLOW}Starting Ollama service...${NC}"
    ollama serve &> /dev/null &
    sleep 3
fi
echo -e "${GREEN}✓ Ollama is running${NC}"
echo ""

# Determine which script to run
case $MODE in
    web)
        SCRIPT="web_gui.py"
        ARGS="--host $HOST --port $PORT"
        ;;
    basic)
        SCRIPT="app_gradio.py"
        ARGS="--host $HOST --port $PORT"
        ;;
    cli)
        SCRIPT="app.py"
        ARGS="--stream"
        NO_PM2=true  # CLI mode must run in foreground
        ;;
esac

# Run with or without PM2
if [ "$NO_PM2" = true ]; then
    echo -e "${GREEN}Starting in foreground mode...${NC}"
    echo "  Press Ctrl+C to stop"
    echo ""
    source .venv/bin/activate
    python3 "$SCRIPT" $ARGS
else
    # Check if PM2 is installed
    if ! command -v pm2 &> /dev/null; then
        echo -e "${RED}PM2 not found. Install with: sudo npm install -g pm2${NC}"
        echo "Or run with --no-pm2 for foreground mode."
        exit 1
    fi

    # Check if already running
    if pm2 describe "$APP_NAME" &> /dev/null; then
        echo -e "${YELLOW}Process '$APP_NAME' is already running.${NC}"
        echo ""
        echo "Options:"
        echo "  pm2 restart $APP_NAME    # Restart"
        echo "  pm2 stop $APP_NAME       # Stop"
        echo "  pm2 logs $APP_NAME       # View logs"
        echo ""
        read -p "Restart the process? [y/N] " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            pm2 restart "$APP_NAME"
            echo -e "${GREEN}✓ Process restarted${NC}"
        fi
    else
        echo -e "${GREEN}Starting with PM2...${NC}"
        
        # Create PM2 ecosystem file
        cat > ecosystem.config.js << EOF
module.exports = {
  apps: [{
    name: '${APP_NAME}',
    script: '${PYTHON_PATH}',
    args: '${SCRIPT} ${ARGS}',
    cwd: '${SCRIPT_DIR}',
    interpreter: 'none',
    env: {
      PATH: '${SCRIPT_DIR}/.venv/bin:' + process.env.PATH
    },
    log_file: '${SCRIPT_DIR}/logs/rag.log',
    error_file: '${SCRIPT_DIR}/logs/rag-error.log',
    out_file: '${SCRIPT_DIR}/logs/rag-out.log',
    time: true,
    autorestart: true,
    max_restarts: 10,
    restart_delay: 5000
  }]
};
EOF
        
        # Start with PM2
        pm2 start ecosystem.config.js
        pm2 save 2>/dev/null || true
        
        echo ""
        echo -e "${GREEN}✓ Application started with PM2${NC}"
    fi
    
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════${NC}"
    echo -e "${BLUE}  Application Info${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════${NC}"
    echo ""
    echo "  URL: http://$HOST:$PORT"
    echo "  Process: $APP_NAME"
    echo ""
    echo -e "${BLUE}  PM2 Commands:${NC}"
    echo "    pm2 logs $APP_NAME       # View logs"
    echo "    pm2 monit                # Monitor dashboard"
    echo "    pm2 restart $APP_NAME    # Restart"
    echo "    ./stop.sh                # Stop application"
    echo ""
    
    # Show status
    pm2 list
fi
