"""
JARVIS Speech-to-Text (STT)
============================
Supports two engines:
  1. faster-whisper  — OpenAI Whisper via CTranslate2 (recommended, offline)
  2. Vosk            — Fully offline, lightweight, lower accuracy

Usage:
    stt = STT()
    text = stt.listen()   # Records from mic until silence, returns transcribed text
"""

import io
import time
import wave
import struct
import tempfile
import os
import numpy as np
import pyaudio
from utils.logger import get_logger
import config

log = get_logger("stt")


class STT:
    """Unified speech-to-text. Auto-selects engine from config."""

    def __init__(self):
        self.engine = config.STT_ENGINE
        self._model = None
        self._pa = pyaudio.PyAudio()
        self._load_model()

    # ─── Model Loading ────────────────────────────────────────────────────────

    def _load_model(self):
        if self.engine == "faster-whisper":
            self._load_faster_whisper()
        elif self.engine == "vosk":
            self._load_vosk()
        else:
            raise ValueError(f"Unknown STT engine: {self.engine}")

    def _load_faster_whisper(self):
        """
        faster-whisper: https://github.com/guillaumekln/faster-whisper
        Install: pip install faster-whisper
        Models downloaded on first use (~150MB for base.en).
        """
        try:
            from faster_whisper import WhisperModel

            log.info(
                f"Loading Whisper model '{config.WHISPER_MODEL}' "
                f"on {config.WHISPER_DEVICE} ({config.WHISPER_COMPUTE_TYPE})..."
            )
            self._model = WhisperModel(
                config.WHISPER_MODEL,
                device=config.WHISPER_DEVICE,
                compute_type=config.WHISPER_COMPUTE_TYPE,
            )
            log.info("Whisper model ready")
        except ImportError:
            log.error("faster-whisper not installed. Run: pip install faster-whisper")
            raise

    def _load_vosk(self):
        """
        Vosk: https://alphacephei.com/vosk/
        Install: pip install vosk
        Download model manually to config.VOSK_MODEL_PATH.
        """
        try:
            from vosk import Model, KaldiRecognizer

            if not os.path.exists(config.VOSK_MODEL_PATH):
                raise FileNotFoundError(
                    f"Vosk model not found at {config.VOSK_MODEL_PATH}. "
                    "Download from https://alphacephei.com/vosk/models"
                )
            self._model = Model(config.VOSK_MODEL_PATH)
            log.info(f"Vosk model loaded from {config.VOSK_MODEL_PATH}")
        except ImportError:
            log.error("vosk not installed. Run: pip install vosk")
            raise

    # ─── Audio Recording ─────────────────────────────────────────────────────

    def _record_until_silence(self) -> bytes:
        """
        Record from microphone until silence is detected.
        Returns raw PCM bytes (16kHz, mono, 16-bit).
        """
        stream = self._pa.open(
            rate=config.AUDIO_SAMPLE_RATE,
            channels=config.AUDIO_CHANNELS,
            format=pyaudio.paInt16,
            input=True,
            frames_per_buffer=config.AUDIO_CHUNK_SIZE,
        )

        frames = []
        silent_chunks = 0
        speaking_chunks = 0
        silence_limit = int(
            config.SILENCE_DURATION
            * config.AUDIO_SAMPLE_RATE
            / config.AUDIO_CHUNK_SIZE
        )
        max_chunks = int(
            config.MAX_RECORDING_SECONDS
            * config.AUDIO_SAMPLE_RATE
            / config.AUDIO_CHUNK_SIZE
        )

        log.debug("Recording...")

        try:
            while True:
                data = stream.read(config.AUDIO_CHUNK_SIZE, exception_on_overflow=False)
                frames.append(data)

                # Calculate RMS energy
                pcm = np.frombuffer(data, dtype=np.int16)
                rms = np.sqrt(np.mean(pcm.astype(np.float32) ** 2))

                if rms > config.SILENCE_THRESHOLD:
                    speaking_chunks += 1
                    silent_chunks = 0
                else:
                    silent_chunks += 1

                # Only stop after user has spoken something
                if speaking_chunks > 3 and silent_chunks >= silence_limit:
                    log.debug("Silence detected — stopping recording")
                    break

                if len(frames) >= max_chunks:
                    log.debug("Max recording length reached")
                    break

        finally:
            stream.stop_stream()
            stream.close()

        return b"".join(frames)

    def _pcm_to_wav(self, pcm_data: bytes) -> bytes:
        """Wrap raw PCM bytes in a WAV container."""
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(config.AUDIO_CHANNELS)
            wf.setsampwidth(2)  # 16-bit = 2 bytes
            wf.setframerate(config.AUDIO_SAMPLE_RATE)
            wf.writeframes(pcm_data)
        return buf.getvalue()

    # ─── Transcription ───────────────────────────────────────────────────────

    def listen(self) -> str:
        """
        Record from microphone and transcribe.
        Returns transcribed text (or empty string on failure).
        """
        log.info("Listening for speech...")
        pcm = self._record_until_silence()

        if not pcm:
            return ""

        return self._transcribe(pcm)

    def listen_short(self, max_seconds: float = 3.0) -> str:
        """Record a short clip (for wake-word fallback)."""
        stream = self._pa.open(
            rate=config.AUDIO_SAMPLE_RATE,
            channels=config.AUDIO_CHANNELS,
            format=pyaudio.paInt16,
            input=True,
            frames_per_buffer=config.AUDIO_CHUNK_SIZE,
        )
        chunks = int(
            max_seconds * config.AUDIO_SAMPLE_RATE / config.AUDIO_CHUNK_SIZE
        )
        frames = [
            stream.read(config.AUDIO_CHUNK_SIZE, exception_on_overflow=False)
            for _ in range(chunks)
        ]
        stream.stop_stream()
        stream.close()
        return self._transcribe(b"".join(frames))

    def transcribe_file(self, path: str) -> str:
        """Transcribe an audio file directly."""
        import soundfile as sf

        audio, sr = sf.read(path)
        if sr != config.AUDIO_SAMPLE_RATE:
            import resampy
            audio = resampy.resample(audio, sr, config.AUDIO_SAMPLE_RATE)

        pcm = (audio * 32767).astype(np.int16).tobytes()
        return self._transcribe(pcm)

    def _transcribe(self, pcm: bytes) -> str:
        if self.engine == "faster-whisper":
            return self._transcribe_whisper(pcm)
        elif self.engine == "vosk":
            return self._transcribe_vosk(pcm)
        return ""

    def _transcribe_whisper(self, pcm: bytes) -> str:
        """Transcribe with faster-whisper."""
        import numpy as np

        # Convert to float32 numpy array
        audio = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0

        t0 = time.time()
        segments, info = self._model.transcribe(
            audio,
            language="en",
            beam_size=5,
            vad_filter=True,  # Skip silent regions
            vad_parameters={"min_silence_duration_ms": 500},
        )

        text = " ".join(s.text.strip() for s in segments).strip()
        elapsed = time.time() - t0
        log.info(f"STT result ({elapsed:.1f}s): '{text}'")
        return text

    def _transcribe_vosk(self, pcm: bytes) -> str:
        """Transcribe with Vosk."""
        import json
        from vosk import KaldiRecognizer

        rec = KaldiRecognizer(self._model, config.AUDIO_SAMPLE_RATE)
        chunk = 4000

        for i in range(0, len(pcm), chunk):
            rec.AcceptWaveform(pcm[i : i + chunk])

        result = json.loads(rec.FinalResult())
        text = result.get("text", "").strip()
        log.info(f"STT result (Vosk): '{text}'")
        return text

    def __del__(self):
        try:
            self._pa.terminate()
        except Exception:
            pass
