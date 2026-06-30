#!/bin/bash
# Setup script for Raspberry Pi 5 Local RAG
# Installs dependencies, pulls Ollama models, and sets up PM2

set -e

echo "=========================================="
echo "  Raspberry Pi 5 Local RAG Setup"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check Python version
echo -e "${YELLOW}[1/6] Checking Python version...${NC}"
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
    echo -e "${GREEN}  ✓ Python $PYTHON_VERSION found${NC}"
else
    echo -e "${RED}  ✗ Python 3 not found. Please install Python 3.10+${NC}"
    exit 1
fi

# Create virtual environment
echo ""
echo -e "${YELLOW}[2/6] Setting up Python virtual environment...${NC}"
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    echo -e "${GREEN}  ✓ Virtual environment created${NC}"
else
    echo -e "${GREEN}  ✓ Virtual environment already exists${NC}"
fi

# Activate virtual environment and install dependencies
echo ""
echo -e "${YELLOW}[3/6] Installing Python dependencies...${NC}"
source .venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo -e "${GREEN}  ✓ Dependencies installed${NC}"

# Check and install Node.js and PM2
echo ""
echo -e "${YELLOW}[4/6] Checking PM2 process manager...${NC}"
if command -v node &> /dev/null; then
    echo -e "${GREEN}  ✓ Node.js found${NC}"
else
    echo -e "${YELLOW}  Installing Node.js...${NC}"
    if command -v apt &> /dev/null; then
        sudo apt update -qq
        sudo apt install -y nodejs npm -qq
    elif command -v brew &> /dev/null; then
        brew install node
    else
        echo -e "${RED}  ✗ Cannot install Node.js automatically${NC}"
        echo "  Please install Node.js manually: https://nodejs.org/"
        exit 1
    fi
    echo -e "${GREEN}  ✓ Node.js installed${NC}"
fi

if command -v pm2 &> /dev/null; then
    echo -e "${GREEN}  ✓ PM2 found${NC}"
else
    echo -e "${YELLOW}  Installing PM2...${NC}"
    sudo npm install -g pm2 -q
    echo -e "${GREEN}  ✓ PM2 installed${NC}"
fi

# Check if Ollama is installed
echo ""
echo -e "${YELLOW}[5/6] Checking Ollama installation...${NC}"
if command -v ollama &> /dev/null; then
    echo -e "${GREEN}  ✓ Ollama is installed${NC}"
else
    echo -e "${RED}  ✗ Ollama not found${NC}"
    echo ""
    echo "  Please install Ollama from https://ollama.com"
    echo "  On Linux/Raspberry Pi:"
    echo "    curl -fsSL https://ollama.com/install.sh | sh"
    echo ""
    echo "  After installing Ollama, run this script again."
    exit 1
fi

# Pull Ollama models
echo ""
echo -e "${YELLOW}[6/6] Pulling Ollama models...${NC}"
echo "  This may take a while on first run..."
echo ""

# Check if Ollama is running
if ! ollama list &> /dev/null; then
    echo -e "${YELLOW}  Starting Ollama service...${NC}"
    ollama serve &> /dev/null &
    sleep 3
fi

# Pull required models
echo -e "  ${YELLOW}Pulling embedding model (nomic-embed-text)...${NC}"
ollama pull nomic-embed-text
echo -e "  ${GREEN}✓ nomic-embed-text ready${NC}"

echo -e "  ${YELLOW}Pulling LLM model (llama3.2:3b)...${NC}"
ollama pull llama3.2:3b
echo -e "  ${GREEN}✓ llama3.2:3b ready${NC}"

echo -e "  ${YELLOW}Pulling reranking model (bge-reranker-base)...${NC}"
if ollama pull bge-reranker-base 2>/dev/null; then
    echo -e "  ${GREEN}✓ bge-reranker-base ready${NC}"
else
    echo -e "  ${YELLOW}⚠ bge-reranker-base not available, will use LLM fallback for reranking${NC}"
fi

# Create data directories
echo ""
echo -e "${YELLOW}Creating data directories...${NC}"
mkdir -p chroma_db rag_storage uploads logs
echo -e "${GREEN}  ✓ Directories created${NC}"

# Setup PM2 startup (optional)
echo ""
echo -e "${YELLOW}Setting up PM2 startup...${NC}"
pm2 startup 2>/dev/null || true
echo -e "${GREEN}  ✓ PM2 configured${NC}"

# Done
echo ""
echo "=========================================="
echo -e "${GREEN}  Setup Complete!${NC}"
echo "=========================================="
echo ""
echo "To start the RAG application, run:"
echo "  ./run.sh"
echo ""
echo "PM2 Commands:"
echo "  ./run.sh           # Start with PM2"
echo "  ./stop.sh          # Stop application"
echo "  pm2 logs rag       # View logs"
echo "  pm2 monit          # Monitor processes"
echo ""
