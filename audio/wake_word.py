"""
JARVIS Wake Word Detection
===========================
Supports two engines:
  1. openWakeWord  — fully free, open-source, runs offline
  2. Porcupine     — Picovoice (free tier, requires access key)

Engine is selected via config.WAKE_WORD_ENGINE.

Usage:
    detector = WakeWordDetector()
    detector.listen(callback=on_wake)   # blocks; calls on_wake() when triggered
"""

import time
import struct
import pyaudio
import numpy as np
from utils.logger import get_logger
import config

log = get_logger("wake_word")


class WakeWordDetector:
    """Unified wake-word detector. Auto-selects engine from config."""

    def __init__(self):
        self.engine = config.WAKE_WORD_ENGINE
        self._pa = None
        self._stream = None
        self._detector = None
        self._running = False
        self._setup()

    # ─── Setup ───────────────────────────────────────────────────────────────

    def _setup(self):
        if self.engine == "openwakeword":
            self._setup_openwakeword()
        elif self.engine == "porcupine":
            self._setup_porcupine()
        else:
            raise ValueError(f"Unknown wake-word engine: {self.engine}")

    def _setup_openwakeword(self):
        """
        openWakeWord — https://github.com/dscripka/openWakeWord
        Install: pip install openwakeword
        Models auto-downloaded on first run.
        """
        try:
            import openwakeword
            from openwakeword.model import Model

            # Download models if not cached
            openwakeword.utils.download_models()

            # Use the built-in "hey jarvis" model
            # Available models: hey_jarvis, alexa, hey_siri, ok_google, etc.
            self._detector = Model(
                wakeword_models=["hey_jarvis"],
                inference_framework="onnx",
            )
            log.info("openWakeWord initialized — model: hey_jarvis")
        except ImportError:
            log.error("openWakeWord not installed. Run: pip install openwakeword")
            raise

    def _setup_porcupine(self):
        """
        Picovoice Porcupine — https://picovoice.ai
        Install: pip install pvporcupine
        Requires free access key from console.picovoice.ai
        """
        try:
            import pvporcupine

            if not config.PORCUPINE_ACCESS_KEY:
                raise ValueError(
                    "Set PORCUPINE_ACCESS_KEY in config.py. "
                    "Get a free key at console.picovoice.ai"
                )

            self._detector = pvporcupine.create(
                access_key=config.PORCUPINE_ACCESS_KEY,
                keywords=["jarvis"],
                sensitivities=[config.WAKE_WORD_SENSITIVITY],
            )
            log.info("Porcupine initialized — keyword: jarvis")
        except ImportError:
            log.error("pvporcupine not installed. Run: pip install pvporcupine")
            raise

    # ─── Listen ──────────────────────────────────────────────────────────────

    def listen(self, callback=None):
        """
        Blocking loop. Reads from microphone, detects wake word.
        Calls callback() when triggered (or returns True if no callback).
        """
        self._running = True
        self._pa = pyaudio.PyAudio()

        if self.engine == "openwakeword":
            self._listen_openwakeword(callback)
        elif self.engine == "porcupine":
            self._listen_porcupine(callback)

    def _listen_openwakeword(self, callback):
        chunk_size = 1280  # openWakeWord expects 80ms @ 16kHz

        stream = self._pa.open(
            rate=16000,
            channels=1,
            format=pyaudio.paInt16,
            input=True,
            frames_per_buffer=chunk_size,
        )
        log.info(f"Listening for wake word: '{config.WAKE_WORD}' (openWakeWord)")

        try:
            while self._running:
                audio_chunk = np.frombuffer(
                    stream.read(chunk_size, exception_on_overflow=False),
                    dtype=np.int16,
                )
                self._detector.predict(audio_chunk)

                # Check all model scores
                for model_name, score in self._detector.prediction_buffer.items():
                    score_val = list(score)[-1]  # Latest score
                    if score_val >= config.WAKE_WORD_SENSITIVITY:
                        log.info(f"Wake word detected! Score: {score_val:.3f}")
                        if callback:
                            callback()
                        else:
                            return True
                        # Reset to avoid repeated triggers
                        time.sleep(1.0)
                        self._detector.reset()
        finally:
            stream.stop_stream()
            stream.close()
            self._pa.terminate()

    def _listen_porcupine(self, callback):
        frame_length = self._detector.frame_length

        stream = self._pa.open(
            rate=self._detector.sample_rate,
            channels=1,
            format=pyaudio.paInt16,
            input=True,
            frames_per_buffer=frame_length,
        )
        log.info(f"Listening for wake word: 'jarvis' (Porcupine)")

        try:
            while self._running:
                raw = stream.read(frame_length, exception_on_overflow=False)
                pcm = struct.unpack_from("h" * frame_length, raw)
                keyword_index = self._detector.process(pcm)
                if keyword_index >= 0:
                    log.info("Wake word detected! (Porcupine)")
                    if callback:
                        callback()
                    else:
                        return True
                    time.sleep(1.0)
        finally:
            stream.stop_stream()
            stream.close()
            self._pa.terminate()
            self._detector.delete()

    def stop(self):
        """Stop the listening loop."""
        self._running = False


# ─── Minimal fallback: keyword spotting without ML ──────────────────────────

class KeywordSpotter:
    """
    Ultra-lightweight fallback using STT + keyword matching.
    No extra dependencies — uses the same STT pipeline.
    Trade-off: higher latency, no true continuous detection.
    """

    def __init__(self, stt_instance):
        self.stt = stt_instance
        self.wake_phrase = config.WAKE_WORD.lower()
        log.info(f"KeywordSpotter initialized — phrase: '{self.wake_phrase}'")

    def listen_once(self) -> bool:
        """Listen for a short clip and return True if wake phrase detected."""
        text = self.stt.listen_short(max_seconds=3)
        if text and self.wake_phrase in text.lower():
            log.info(f"Wake phrase spotted in: '{text}'")
            return True
        return False
