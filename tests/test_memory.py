"""
Tests for the Memory system.
Uses an in-memory / temp database — no side effects on real data.
Run with: pytest tests/test_memory.py -v
"""

import sys
import os
import tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest


class TestMemory:

    def setup_method(self):
        """Each test gets a fresh in-memory memory instance."""
        import config
        # Point to a temp DB so we don't pollute real data
        self._orig_db = config.MEMORY_DB
        config.MEMORY_DB = ":memory:"
        config.LONG_TERM_MEMORY_ENABLED = True

        from brain.memory import Memory
        self.mem = Memory()

    def teardown_method(self):
        import config
        self.mem.close()
        config.MEMORY_DB = self._orig_db

    def test_short_term_add_and_retrieve(self):
        self.mem.add_exchange("Hello", "Hi there!")
        history = self.mem.get_short_term()
        assert len(history) == 1
        assert history[0]["role_user"] == "Hello"
        assert history[0]["role_assistant"] == "Hi there!"

    def test_short_term_respects_max_size(self):
        import config
        for i in range(config.SHORT_TERM_MEMORY_SIZE + 5):
            self.mem.add_exchange(f"msg {i}", f"resp {i}")
        assert len(self.mem.get_short_term()) == config.SHORT_TERM_MEMORY_SIZE

    def test_clear_short_term(self):
        self.mem.add_exchange("test", "response")
        self.mem.clear_short_term()
        assert len(self.mem.get_short_term()) == 0

    def test_remember_and_recall(self):
        self.mem.remember("user_name", "Mann")
        assert self.mem.recall("user_name") == "Mann"

    def test_recall_missing_key_returns_none(self):
        assert self.mem.recall("nonexistent_key") is None

    def test_forget(self):
        self.mem.remember("temp_key", "temp_value")
        self.mem.forget("temp_key")
        assert self.mem.recall("temp_key") is None

    def test_remember_overwrites_existing(self):
        self.mem.remember("city", "New York")
        self.mem.remember("city", "Chicago")
        assert self.mem.recall("city") == "Chicago"

    def test_get_all_facts(self):
        self.mem.remember("a", "1")
        self.mem.remember("b", "2")
        facts = self.mem.get_all_facts()
        assert "a" in facts
        assert "b" in facts

    def test_context_prompt_includes_facts(self):
        self.mem.remember("user_name", "Mann")
        ctx = self.mem.get_context_prompt()
        assert "Mann" in ctx
        assert "user_name" in ctx

    def test_extract_name_from_message(self):
        self.mem.extract_and_store_facts("my name is Alex")
        assert self.mem.recall("user_name") == "Alex"

    def test_extract_location_from_message(self):
        self.mem.extract_and_store_facts("I live in Boston")
        assert self.mem.recall("user_location") == "Boston"

    def test_get_messages_for_llm_format(self):
        self.mem.add_exchange("What is Python?", "Python is a language.")
        msgs = self.mem.get_messages_for_llm()
        assert msgs[0]["role"] == "user"
        assert msgs[1]["role"] == "assistant"
        assert msgs[0]["content"] == "What is Python?"
