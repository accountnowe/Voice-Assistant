#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════
# JARVIS Setup Script — macOS
# ═══════════════════════════════════════════════════════════════════════
# Run: chmod +x setup.sh && ./setup.sh
# ═══════════════════════════════════════════════════════════════════════

set -e  # Exit on error

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo ""
echo "╔═══════════════════════════════════════╗"
echo "║   JARVIS Setup — macOS                ║"
echo "╚═══════════════════════════════════════╝"
echo ""

# ─── 1. Check Python ────────────────────────────────────────────────────────
echo -e "${GREEN}[1/7] Checking Python version...${NC}"
python3.11 --version || { echo -e "${RED}Python 3.9+ required. Install from python.org${NC}"; exit 1; }
PY_VER=$(python3.11 -c "import sys; print(sys.version_info.minor)")
if [ "$PY_VER" -lt 9 ]; then
    echo -e "${RED}Python 3.9+ required (found 3.${PY_VER})${NC}"
    exit 1
fi
echo "  ✓ Python OK"

# ─── 2. Install Homebrew if needed ──────────────────────────────────────────
echo -e "${GREEN}[2/7] Checking Homebrew...${NC}"
if ! command -v brew &> /dev/null; then
    echo "  Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi
echo "  ✓ Homebrew OK"

# ─── 3. Install system dependencies ─────────────────────────────────────────
echo -e "${GREEN}[3/7] Installing system dependencies...${NC}"
brew install portaudio python@3.11 || true
echo "  ✓ System deps OK"

# ─── 4. Create virtual environment ──────────────────────────────────────────
echo -e "${GREEN}[4/7] Creating virtual environment...${NC}"
if [ ! -d "venv" ]; then
    python3.11 -m venv venv
fi
source venv/bin/activate
pip install --upgrade pip --quiet
echo "  ✓ Virtual env ready (venv/)"

# ─── 5. Install Python packages ──────────────────────────────────────────────
echo -e "${GREEN}[5/7] Installing Python packages...${NC}"
echo "  This may take 2–5 minutes on first run..."

pip install --quiet requests numpy pyaudio
echo "  ✓ Core packages"

pip install --quiet openwakeword
echo "  ✓ Wake word (openWakeWord)"

pip install --quiet faster-whisper
echo "  ✓ Speech-to-text (Whisper)"

pip install --quiet pyttsx3
echo "  ✓ Text-to-speech (pyttsx3)"

pip install --quiet pymupdf
echo "  ✓ PDF reader (PyMuPDF)"

pip install --quiet duckduckgo-search psutil
echo "  ✓ Search + system utils"

# ─── 6. Install Ollama ───────────────────────────────────────────────────────
echo -e "${GREEN}[6/7] Installing Ollama...${NC}"
if ! command -v ollama &> /dev/null; then
    echo "  Downloading Ollama..."
    curl -fsSL https://ollama.ai/install.sh | sh
    echo "  ✓ Ollama installed"
else
    echo "  ✓ Ollama already installed"
fi

# ─── 7. Pull LLM model ───────────────────────────────────────────────────────
echo -e "${GREEN}[7/7] Setting up LLM model...${NC}"
echo ""
echo "  Which model would you like? (Enter number)"
echo "  1) phi3:mini    — ~2GB, best for low RAM (8GB or less)"
echo "  2) gemma2:2b    — ~2GB, fast and smart"
echo "  3) mistral      — ~4GB, best quality/speed ★ (recommended)"
echo "  4) llama3.2     — ~4GB, excellent reasoning"
echo "  5) Skip (I'll pull manually later)"
echo ""
read -p "  Choice [3]: " MODEL_CHOICE
MODEL_CHOICE=${MODEL_CHOICE:-3}

case $MODEL_CHOICE in
    1) MODEL="phi3:mini" ;;
    2) MODEL="gemma2:2b" ;;
    3) MODEL="mistral" ;;
    4) MODEL="llama3.2" ;;
    5) MODEL="" ;;
    *) MODEL="mistral" ;;
esac

if [ -n "$MODEL" ]; then
    echo "  Starting Ollama and pulling $MODEL..."
    ollama serve &>/dev/null &
    OLLAMA_PID=$!
    sleep 3
    ollama pull "$MODEL"
    kill $OLLAMA_PID 2>/dev/null || true
    echo "  ✓ Model '$MODEL' ready"

    # Update config.py with chosen model
    sed -i '' "s/OLLAMA_MODEL = .*/OLLAMA_MODEL = \"$MODEL\"/" config.py
    echo "  ✓ config.py updated"
fi

# ─── Done ────────────────────────────────────────────────────────────────────
echo ""
echo "╔═══════════════════════════════════════════════════════╗"
echo "║   ✓ JARVIS setup complete!                            ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo ""
echo "  To run JARVIS:"
echo ""
echo "    source venv/bin/activate     # Activate virtual env"
echo "    ollama serve &               # Start Ollama (if not running)"
echo "    python main.py               # Launch JARVIS"
echo ""
echo "  Flags:"
echo "    python main.py --no-wake     # Skip wake word (press Enter)"
echo "    python main.py --text        # Text-only mode"
echo "    python main.py --model phi3  # Use a different model"
echo ""
echo "  First run will download Whisper model (~150MB). Please wait."
echo ""
