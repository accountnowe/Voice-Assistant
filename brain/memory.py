from typing import Optional, List, Dict
"""

from typing import Optional, List, Dict
JARVIS Memory System
====================
Two-tier memory:

  Short-term — In-memory deque of recent exchanges (cleared on restart)
  Long-term  — SQLite database (persists across restarts)

Long-term memory stores:
  - Named facts  ("My name is Mann", "I live in NYC")
  - Preferences  ("I prefer dark mode", "Call me Boss")
  - Past context (date-stamped summaries of previous sessions)

Usage:
    mem = Memory()
    mem.add_exchange("What's the weather?", "It's 72°F and sunny.")
    mem.remember("user_name", "Mann")
    name = mem.recall("user_name")
    context = mem.get_context_prompt()
"""

from typing import Optional, List, Dict

import sqlite3
import json
from collections import deque
from datetime import datetime
from utils.logger import get_logger
import config

log = get_logger("memory")


class Memory:
    """Two-tier memory system for JARVIS."""

    def __init__(self):
        self._short_term = deque(maxlen=config.SHORT_TERM_MEMORY_SIZE)
        self._db = None

        if config.LONG_TERM_MEMORY_ENABLED:
            self._init_db()

    # ─── DB Setup ─────────────────────────────────────────────────────────────

    def _init_db(self):
        """Initialize SQLite database."""
        self._db = sqlite3.connect(config.MEMORY_DB, check_same_thread=False)
        self._db.row_factory = sqlite3.Row

        self._db.executescript("""
            CREATE TABLE IF NOT EXISTS facts (
                key         TEXT PRIMARY KEY,
                value       TEXT NOT NULL,
                category    TEXT DEFAULT 'general',
                created_at  TEXT NOT NULL,
                updated_at  TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS session_log (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp   TEXT NOT NULL,
                user_msg    TEXT NOT NULL,
                jarvis_msg  TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS session_summaries (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                date        TEXT NOT NULL,
                summary     TEXT NOT NULL
            );
        """)
        self._db.commit()
        log.info(f"Memory DB initialized: {config.MEMORY_DB}")

    # ─── Short-Term ───────────────────────────────────────────────────────────

    def add_exchange(self, user: str, assistant: str):
        """Add a user/assistant exchange to short-term memory."""
        self._short_term.append({
            "role_user": user,
            "role_assistant": assistant,
            "ts": datetime.now().isoformat(),
        })

        if self._db:
            self._db.execute(
                "INSERT INTO session_log (timestamp, user_msg, jarvis_msg) VALUES (?, ?, ?)",
                (datetime.now().isoformat(), user, assistant),
            )
            self._db.commit()

    def get_short_term(self) -> List[Dict]:
        """Return recent exchanges as list of dicts."""
        return list(self._short_term)

    def get_messages_for_llm(self) -> List[Dict]:
        """
        Format short-term memory as OpenAI-style messages.
        Compatible with Ollama's chat endpoint.
        """
        messages = []
        for ex in self._short_term:
            messages.append({"role": "user", "content": ex["role_user"]})
            messages.append({"role": "assistant", "content": ex["role_assistant"]})
        return messages

    def clear_short_term(self):
        """Clear the in-memory conversation history."""
        self._short_term.clear()
        log.info("Short-term memory cleared")

    # ─── Long-Term Facts ──────────────────────────────────────────────────────

    def remember(self, key: str, value: str, category: str = "general"):
        """Store a named fact persistently."""
        if not self._db:
            return
        now = datetime.now().isoformat()
        self._db.execute(
            """INSERT INTO facts (key, value, category, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(key) DO UPDATE SET value=?, category=?, updated_at=?""",
            (key, value, category, now, now, value, category, now),
        )
        self._db.commit()
        log.info(f"Remembered: {key} = {value}")

    def recall(self, key: str) -> Optional[str]:
        """Retrieve a stored fact by key."""
        if not self._db:
            return None
        row = self._db.execute(
            "SELECT value FROM facts WHERE key = ?", (key,)
        ).fetchone()
        return row["value"] if row else None

    def forget(self, key: str):
        """Delete a stored fact."""
        if self._db:
            self._db.execute("DELETE FROM facts WHERE key = ?", (key,))
            self._db.commit()

    def get_all_facts(self) -> dict:
        """Return all stored facts as a dictionary."""
        if not self._db:
            return {}
        rows = self._db.execute("SELECT key, value, category FROM facts").fetchall()
        return {r["key"]: {"value": r["value"], "category": r["category"]} for r in rows}

    # ─── Context for LLM ─────────────────────────────────────────────────────

    def get_context_prompt(self) -> str:
        """
        Build a short context string to prepend to the system prompt.
        Includes known facts about the user.
        """
        facts = self.get_all_facts()
        if not facts:
            return ""

        lines = ["Context I know about you:"]
        for key, data in facts.items():
            lines.append(f"  - {key}: {data['value']}")

        return "\n".join(lines)

    # ─── Smart Extraction ────────────────────────────────────────────────────

    def extract_and_store_facts(self, user_message: str):
        """
        Simple rule-based extraction of facts from user speech.
        For richer extraction, pass through the LLM.
        """
        import re

        patterns = [
            (r"my name is (\w+)", "user_name"),
            (r"call me (\w+)", "user_name"),
            (r"i(?:'m| am) (\w+)", "user_name"),
            (r"i live in ([a-zA-Z ,]+)", "user_location"),
            (r"i(?:'m| am) from ([a-zA-Z ,]+)", "user_location"),
            (r"i work (?:at|for) ([a-zA-Z0-9 ]+)", "user_employer"),
            (r"i(?:'m| am) a (?:an )?([a-zA-Z ]+)", "user_role"),
        ]

        msg = user_message.lower()
        for pattern, key in patterns:
            match = re.search(pattern, msg)
            if match:
                value = match.group(1).strip().title()
                existing = self.recall(key)
                if existing != value:
                    self.remember(key, value, category="user_info")
                    log.info(f"Auto-extracted fact: {key} = {value}")

    def close(self):
        if self._db:
            self._db.close()
