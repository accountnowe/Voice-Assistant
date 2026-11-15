"""
JARVIS Text-to-Speech (TTS)
============================
Supports three engines (in order of voice quality):
  1. coqui       — High quality neural TTS, fully offline
  2. pyttsx3     — System voices, lightweight, cross-platform
  3. system      — macOS `say` command / Windows SAPI (fastest, lowest quality)

Usage:
    tts = TTS()
    tts.speak("Hello, I am JARVIS.")
    tts.speak_async("Processing your request...")  # Non-blocking
"""

import os
import platform
import subprocess
import threading
import queue
import tempfile
from utils.logger import get_logger
import config

log = get_logger("tts")

PLATFORM = platform.system()


class TTS:
    """Unified text-to-speech engine."""

    def __init__(self, gui=None):
        self.engine_name = config.TTS_ENGINE
        self._engine = None
        self._speak_queue = queue.Queue()
        self._worker_thread = None
        self.gui = gui
        self._setup()
        self._start_worker()

    # ─── Setup ───────────────────────────────────────────────────────────────

    def _setup(self):
        if self.engine_name == "pyttsx3":
            self._setup_pyttsx3()
        elif self.engine_name == "coqui":
            self._setup_coqui()
        elif self.engine_name == "system":
            log.info(f"TTS engine: system ({PLATFORM})")
        else:
            log.warning(f"Unknown TTS engine '{self.engine_name}', falling back to pyttsx3")
            self.engine_name = "pyttsx3"
            self._setup_pyttsx3()

    def _setup_pyttsx3(self):
        """
        pyttsx3: https://pyttsx3.readthedocs.io
        Install: pip install pyttsx3
        Uses system TTS voices (macOS: NSSpeechSynthesizer, Windows: SAPI)
        """
        try:
            import pyttsx3

            self._engine = pyttsx3.init()
            self._engine.setProperty("rate", config.TTS_RATE)
            self._engine.setProperty("volume", config.TTS_VOLUME)

            # Select voice by index
            voices = self._engine.getProperty("voices")
            if voices and config.TTS_VOICE_INDEX < len(voices):
                self._engine.setProperty(
                    "voice", voices[config.TTS_VOICE_INDEX].id
                )
                log.info(
                    f"pyttsx3 voice: {voices[config.TTS_VOICE_INDEX].name}"
                )
            else:
                log.info("pyttsx3 initialized with default voice")

        except ImportError:
            log.error("pyttsx3 not installed. Run: pip install pyttsx3")
            raise

    def _setup_coqui(self):
        """
        Coqui TTS: https://github.com/coqui-ai/TTS
        Install: pip install TTS
        First run downloads ~200MB model.
        """
        try:
            from TTS.api import TTS as CoquiTTS

            log.info(f"Loading Coqui model: {config.COQUI_MODEL}")
            self._engine = CoquiTTS(config.COQUI_MODEL, progress_bar=False)
            log.info("Coqui TTS ready")

        except ImportError:
            log.error("Coqui TTS not installed. Run: pip install TTS")
            log.warning("Falling back to pyttsx3")
            self.engine_name = "pyttsx3"
            self._setup_pyttsx3()

    # ─── Worker Thread ────────────────────────────────────────────────────────

    def _start_worker(self):
        """Start a background worker to serialize TTS calls."""
        self._worker_thread = threading.Thread(
            target=self._worker_loop, daemon=True
        )
        self._worker_thread.start()

    def _worker_loop(self):
        while True:
            text = self._speak_queue.get()
            if text is None:
                break
            try:
                self._speak_sync(text)
            except Exception as e:
                log.error(f"TTS error: {e}")
            finally:
                self._speak_queue.task_done()

    # ─── Public API ──────────────────────────────────────────────────────────

    def speak(self, text: str):
        """Speak text synchronously (blocks until done)."""
        if not text or not text.strip():
            return
        log.info(f"Speaking: {text[:80]}{'...' if len(text) > 80 else ''}")
        if self.gui:
            self.gui.set_state("speaking")
            self.gui.add_message("JARVIS", text)
        self._speak_sync(text)
        if self.gui:
            self.gui.set_state("idle")

    def speak_async(self, text: str):
        """Queue text to be spoken (non-blocking)."""
        if not text or not text.strip():
            return
        self._speak_queue.put(text)

    def stop(self):
        """Stop the worker thread."""
        self._speak_queue.put(None)

    # ─── Engines ─────────────────────────────────────────────────────────────

    def _speak_sync(self, text: str):
        # Clean text for speech (remove markdown, extra symbols)
        text = self._clean_text(text)

        if self.engine_name == "pyttsx3":
            self._speak_pyttsx3(text)
        elif self.engine_name == "coqui":
            self._speak_coqui(text)
        elif self.engine_name == "system":
            self._speak_system(text)

    def _speak_pyttsx3(self, text: str):
        """
        Re-initialize the engine on every call. pyttsx3's Windows SAPI backend
        is known to silently stop producing audio after the first runAndWait()
        call if the same engine instance is reused across multiple speak() calls.
        """
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty("rate", config.TTS_RATE)
        engine.setProperty("volume", config.TTS_VOLUME)
        voices = engine.getProperty("voices")
        if voices and config.TTS_VOICE_INDEX < len(voices):
            engine.setProperty("voice", voices[config.TTS_VOICE_INDEX].id)
        engine.say(text)
        engine.runAndWait()
        engine.stop()

    def _speak_coqui(self, text: str):
        """Generate audio with Coqui and play it."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            tmp_path = f.name

        try:
            self._engine.tts_to_file(text=text, file_path=tmp_path)
            self._play_audio_file(tmp_path)
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def _speak_system(self, text: str):
        """Use platform native TTS."""
        if PLATFORM == "Darwin":
            subprocess.run(
                ["say", "-v", config.SYSTEM_TTS_VOICE, text],
                check=False,
            )
        elif PLATFORM == "Windows":
            # PowerShell SAPI — fresh process every call, avoids pyttsx3's
            # known Windows engine-reuse silent-failure bug
            ps_cmd = (
                f"Add-Type -AssemblyName System.Speech; "
                f"$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                f"$s.SelectVoice('Microsoft Zira Desktop'); "
                f"$s.Speak('{text.replace(chr(39), ' ')}')"
            )
            subprocess.run(
                ["powershell", "-Command", ps_cmd],
                check=False,
                capture_output=True,
            )
        else:
            # Linux fallback: espeak or festival
            for cmd in [["espeak", text], ["festival", "--tts"]]:
                try:
                    subprocess.run(cmd, check=True, capture_output=True)
                    break
                except FileNotFoundError:
                    continue

    def _play_audio_file(self, path: str):
        """Play a WAV file using platform tools."""
        if PLATFORM == "Darwin":
            subprocess.run(["afplay", path], check=False)
        elif PLATFORM == "Windows":
            import winsound
            winsound.PlaySound(path, winsound.SND_FILENAME)
        else:
            for cmd in [["aplay", path], ["paplay", path]]:
                try:
                    subprocess.run(cmd, check=True, capture_output=True)
                    return
                except FileNotFoundError:
                    continue

    # ─── Text Cleaning ────────────────────────────────────────────────────────

    def _clean_text(self, text: str) -> str:
        """
        Remove characters that cause odd TTS pronunciation.
        The LLM is instructed not to use markdown, but this is a safety net.
        """
        import re

        # Remove markdown-style formatting
        text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)  # bold
        text = re.sub(r"\*(.*?)\*", r"\1", text)       # italic
        text = re.sub(r"`(.*?)`", r"\1", text)          # inline code
        text = re.sub(r"#{1,6}\s", "", text)            # headers
        text = re.sub(r"^\s*[-*+]\s", "", text, flags=re.MULTILINE)  # bullets
        text = re.sub(r"\n+", " ", text)                # newlines → space
        text = re.sub(r"\s+", " ", text)

        return text.strip()
