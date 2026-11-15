"""
JARVIS Configuration
====================
Central config for all modules. Edit this file to tune your assistant.
"""

import os
import platform

# ── System ──────────────────────────────────────────────────────────────────
PLATFORM = platform.system()  # "Darwin" | "Windows" | "Linux"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
MEMORY_DB = os.path.join(DATA_DIR, "memory.db")
LOGS_DIR = os.path.join(BASE_DIR, "logs")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

# ── Wake Word ────────────────────────────────────────────────────────────────
WAKE_WORD = "hey jarvis"             # Used by openWakeWord
WAKE_WORD_SENSITIVITY = 0.5          # 0.0 (strict) → 1.0 (loose)
WAKE_WORD_ENGINE = "openwakeword"    # "openwakeword" | "porcupine"
PORCUPINE_ACCESS_KEY = ""            # Only needed if using Picovoice Porcupine

# ── Audio ────────────────────────────────────────────────────────────────────
AUDIO_SAMPLE_RATE = 16000
AUDIO_CHANNELS = 1
AUDIO_CHUNK_SIZE = 1024
SILENCE_THRESHOLD = 500              # RMS threshold for silence detection
SILENCE_DURATION = 1.5               # Seconds of silence to end recording
MAX_RECORDING_SECONDS = 15           # Max clip length before auto-stop

# ── STT (Speech-to-Text) ─────────────────────────────────────────────────────
STT_ENGINE = "faster-whisper"        # "faster-whisper" | "vosk"
WHISPER_MODEL = "base.en"            # tiny.en | base.en | small.en | medium.en
WHISPER_COMPUTE_TYPE = "int8"        # int8 (CPU) | float16 (GPU)
WHISPER_DEVICE = "cpu"               # "cpu" | "cuda"
VOSK_MODEL_PATH = os.path.join(DATA_DIR, "vosk-model")

# ── TTS (Text-to-Speech) ─────────────────────────────────────────────────────
TTS_ENGINE = "system"                # "pyttsx3" | "coqui" | "system"               # "pyttsx3" | "coqui" | "system"
TTS_RATE = 175                       # Words per minute (pyttsx3)
TTS_VOLUME = 0.9                     # 0.0 → 1.0
TTS_VOICE_INDEX = 1                  # Voice index (pyttsx3, platform-specific) — Zira, female

# macOS system TTS (say command) voice options:
# "Alex", "Samantha", "Tom", "Daniel", "Fiona", "Karen"
SYSTEM_TTS_VOICE = "Samantha"        # macOS only

# Coqui TTS model (downloaded on first use)
COQUI_MODEL = "tts_models/en/ljspeech/tacotron2-DDC"

# ── LLM / Brain ──────────────────────────────────────────────────────────────
LLM_ENGINE = "ollama"                # "ollama" | "llamacpp"
OLLAMA_HOST = "http://localhost:11434"
OLLAMA_MODEL = "llama3.2"
OLLAMA_TIMEOUT = 60                  # Seconds before giving up on response
LLM_MAX_TOKENS = 512
LLM_TEMPERATURE = 0.7
LLM_CONTEXT_WINDOW = 8              # Messages to keep in context (not tokens)

# ── Personality ───────────────────────────────────────────────────────────────
PERSONALITY_MODE = "default"         # "default" | "formal" | "funny" | "sarcastic"

PERSONALITY_PROMPTS = {
    "default": (
        "You are JARVIS, a helpful and intelligent AI assistant. "
        "You are concise, friendly, and practical. "
        "Keep responses short and conversational — you are being spoken aloud via TTS. "
        "Never use markdown formatting, bullet points, or special characters in your responses. "
        "Speak in plain, natural sentences."
    ),
    "formal": (
        "You are JARVIS, a highly professional AI assistant. "
        "You respond with precision, formality, and expertise. "
        "Keep responses concise for voice delivery. Use no markdown or special characters."
    ),
    "funny": (
        "You are JARVIS, a witty and humorous AI assistant. "
        "You answer helpfully but with humor, light sarcasm, and occasional jokes. "
        "Keep it clean and concise. No markdown or special characters."
    ),
    "sarcastic": (
        "You are JARVIS, a sarcastic but ultimately helpful AI assistant. "
        "You respond with dry wit and mild sarcasm, but always provide the actual answer. "
        "Keep it concise. No markdown or special characters."
    ),
}

# ── Memory ───────────────────────────────────────────────────────────────────
MEMORY_ENABLED = True
SHORT_TERM_MEMORY_SIZE = 10          # Number of recent exchanges to hold
LONG_TERM_MEMORY_ENABLED = True      # Persist facts to SQLite

# ── Weather ───────────────────────────────────────────────────────────────────
# Uses wttr.in — no API key required
DEFAULT_LOCATION = "New York"        # Fallback if location not detected
WEATHER_TIMEOUT = 5                  # Seconds before timeout

# ── Actions ───────────────────────────────────────────────────────────────────
# App name aliases — maps spoken names → actual app names
APP_ALIASES = {
    "chrome": "chrome.exe",
    "google chrome": "chrome.exe",
    "browser": "chrome.exe",
    "firefox": "firefox.exe",
    "vscode": "Code.exe",
    "vs code": "Code.exe",
    "core": "Code.exe",
    "cord": "Code.exe",
    "code": "Code.exe",
    "terminal": "wt",                    # Windows Terminal — only if installed
    "calculator": "calc",
    "slack": "slack.exe",
    "discord": "Discord.exe",            # unreliable — see note below
    "zoom": "Zoom.exe",
    "notion": "Notion.exe",              # unreliable — see note below
    "word": "WINWORD.EXE",
    "excel": "EXCEL.EXE",
    "powerpoint": "POWERPNT.EXE",
    "spotify": "Spotify.exe",
}
# PDF summarization chunk size (characters)
PDF_CHUNK_SIZE = 3000

# ── Debug ─────────────────────────────────────────────────────────────────────
DEBUG_MODE = False
LOG_LEVEL = "INFO"                   # DEBUG | INFO | WARNING | ERROR
LOG_TO_FILE = True
