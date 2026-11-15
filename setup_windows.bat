@echo off
REM ═══════════════════════════════════════════════════════════════════════
REM JARVIS Setup Script — Windows
REM ═══════════════════════════════════════════════════════════════════════
REM Run as Administrator for best results.
REM Requirements: Python 3.9+, pip, winget (Windows 11) or manual Ollama install
REM ═══════════════════════════════════════════════════════════════════════

echo.
echo  ╔═══════════════════════════════════════╗
echo  ║   JARVIS Setup — Windows              ║
echo  ╚═══════════════════════════════════════╝
echo.

REM ─── Check Python ─────────────────────────────────────────────────────────
echo [1/6] Checking Python...
python --version > NUL 2>&1
IF ERRORLEVEL 1 (
    echo ERROR: Python not found. Download from https://python.org
    pause
    exit /b 1
)
echo   OK: Python found

REM ─── Create virtual environment ───────────────────────────────────────────
echo [2/6] Creating virtual environment...
IF NOT EXIST venv (
    python -m venv venv
)
call venv\Scripts\activate.bat
pip install --upgrade pip --quiet
echo   OK: Virtual env ready

REM ─── Install PyAudio ──────────────────────────────────────────────────────
echo [3/6] Installing audio dependencies...
pip install pipwin --quiet
pipwin install pyaudio
echo   OK: PyAudio installed

REM ─── Install Python packages ──────────────────────────────────────────────
echo [4/6] Installing Python packages (this takes 2-5 minutes)...
pip install requests numpy --quiet
pip install openwakeword --quiet
pip install faster-whisper --quiet
pip install pyttsx3 --quiet
pip install pymupdf --quiet
pip install duckduckgo-search psutil --quiet
echo   OK: All packages installed

REM ─── Install Ollama ───────────────────────────────────────────────────────
echo [5/6] Installing Ollama...
where ollama > NUL 2>&1
IF ERRORLEVEL 1 (
    echo   Downloading Ollama installer...
    winget install Ollama.Ollama
    echo   OK: Ollama installed
) ELSE (
    echo   OK: Ollama already installed
)

REM ─── Pull LLM model ───────────────────────────────────────────────────────
echo [6/6] Pulling LLM model (mistral ~4GB)...
echo   This will take several minutes depending on your internet speed.
echo   Press Ctrl+C to skip and pull manually later with: ollama pull mistral
start /B ollama serve
timeout /t 3 /nobreak > NUL
ollama pull mistral
echo   OK: Model ready

echo.
echo  ╔═══════════════════════════════════════════════════════╗
echo  ║   OK: JARVIS setup complete!                          ║
echo  ╚═══════════════════════════════════════════════════════╝
echo.
echo   To run JARVIS:
echo.
echo     venv\Scripts\activate          ^| Activate virtual env
echo     start ollama serve             ^| Start Ollama
echo     python main.py                 ^| Launch JARVIS
echo.
echo   Text-only mode (no mic needed):
echo     python main.py --text
echo.
pause
