"""
Tests for configuration validity.
Ensures config.py has all required keys and valid values.
Run with: pytest tests/test_config.py -v
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import config


class TestConfig:

    def test_personality_prompts_all_present(self):
        required = ["default", "formal", "funny", "sarcastic"]
        for mode in required:
            assert mode in config.PERSONALITY_PROMPTS, f"Missing personality: {mode}"

    def test_personality_prompts_non_empty(self):
        for mode, prompt in config.PERSONALITY_PROMPTS.items():
            assert len(prompt) > 50, f"Personality '{mode}' prompt is too short"

    def test_valid_stt_engine(self):
        assert config.STT_ENGINE in ("faster-whisper", "vosk")

    def test_valid_tts_engine(self):
        assert config.TTS_ENGINE in ("pyttsx3", "coqui", "system")

    def test_valid_wake_word_sensitivity(self):
        assert 0.0 <= config.WAKE_WORD_SENSITIVITY <= 1.0

    def test_valid_llm_temperature(self):
        assert 0.0 <= config.LLM_TEMPERATURE <= 2.0

    def test_data_and_logs_dirs_created(self):
        assert os.path.isdir(config.DATA_DIR)
        assert os.path.isdir(config.LOGS_DIR)

    def test_app_aliases_values_are_strings(self):
        for k, v in config.APP_ALIASES.items():
            assert isinstance(k, str)
            assert isinstance(v, str)

    def test_silence_threshold_is_positive(self):
        assert config.SILENCE_THRESHOLD > 0

    def test_whisper_model_valid(self):
        valid = ("tiny", "tiny.en", "base", "base.en", "small",
                 "small.en", "medium", "medium.en", "large")
        assert config.WHISPER_MODEL in valid
