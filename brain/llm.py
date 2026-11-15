from typing import Optional, List, Dict
"""

from typing import Optional, List, Dict
JARVIS LLM Interface
====================
Interfaces with a locally-running Ollama instance.

Prerequisites:
  1. Install Ollama: https://ollama.ai
  2. Pull a model: ollama pull mistral
  3. Start Ollama: ollama serve  (or it starts automatically)

Recommended models (pick based on your hardware):
  ┌─────────────────┬──────────┬──────────────────────────────────────┐
  │ Model           │ RAM Req  │ Notes                                │
  ├─────────────────┼──────────┼──────────────────────────────────────┤
  │ phi3:mini       │ ~3 GB    │ Best for low-spec hardware           │
  │ gemma2:2b       │ ~3 GB    │ Fast, solid reasoning                │
  │ mistral         │ ~5 GB    │ Best quality/speed balance ★         │
  │ llama3.2        │ ~5 GB    │ Great instruction following          │
  │ mistral:7b-q4   │ ~4 GB    │ Quantized mistral (less RAM)         │
  │ llama3.1:8b     │ ~6 GB    │ Strong, versatile                    │
  └─────────────────┴──────────┴──────────────────────────────────────┘

Usage:
    llm = LLM(memory)
    response = llm.chat("What's the capital of France?")
"""

from typing import Optional, List, Dict

import json
import time
import requests
from utils.logger import get_logger
import config

log = get_logger("llm")


class LLM:
    """Ollama-backed LLM with personality + memory integration."""

    def __init__(self, memory=None):
        self.memory = memory
        self._base_url = config.OLLAMA_HOST
        self._model = config.OLLAMA_MODEL
        self._personality = config.PERSONALITY_MODE
        self._check_ollama()

    # ─── Health Check ─────────────────────────────────────────────────────────

    def _check_ollama(self):
        """Verify Ollama is running and the model is available."""
        try:
            resp = requests.get(f"{self._base_url}/api/tags", timeout=3)
            models = [m["name"] for m in resp.json().get("models", [])]
            log.info(f"Ollama running. Available models: {', '.join(models) or 'none'}")

            # Warn if configured model isn't pulled
            model_base = self._model.split(":")[0]
            if not any(model_base in m for m in models):
                log.warning(
                    f"Model '{self._model}' not found. "
                    f"Run: ollama pull {self._model}"
                )

        except requests.exceptions.ConnectionError:
            log.error(
                "Ollama not running! Start it with: ollama serve\n"
                "Install from: https://ollama.ai"
            )

    def is_ollama_running(self) -> bool:
        try:
            requests.get(f"{self._base_url}/api/tags", timeout=2)
            return True
        except Exception:
            return False

    # ─── Core Chat ────────────────────────────────────────────────────────────

    def chat(self, user_message: str, extract_facts: bool = True) -> str:
        """
        Send a message and get a response.
        Automatically injects memory context and conversation history.
        """
        messages = self._build_messages(user_message)

        t0 = time.time()
        try:
            response = requests.post(
                f"{self._base_url}/api/chat",
                json={
                    "model": self._model,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "temperature": config.LLM_TEMPERATURE,
                        "num_predict": config.LLM_MAX_TOKENS,
                    },
                },
                timeout=config.OLLAMA_TIMEOUT,
            )
            response.raise_for_status()
            result = response.json()
            reply = result["message"]["content"].strip()

        except requests.exceptions.Timeout:
            reply = "I'm sorry, the response took too long. Please try again."
            log.error("LLM request timed out")
        except requests.exceptions.ConnectionError:
            reply = "I can't reach the brain. Make sure Ollama is running."
            log.error("Ollama connection error")
        except Exception as e:
            reply = "I encountered an error processing your request."
            log.error(f"LLM error: {e}")

        elapsed = time.time() - t0
        log.info(f"LLM response ({elapsed:.1f}s): {reply[:100]}...")

        # Store in memory
        # Store in memory
        if self.memory:
            self.memory.add_exchange(user_message, reply)
            if extract_facts:
                self.memory.extract_and_store_facts(user_message)

        return reply

    def chat_with_context(self, user_message: str, extra_context: str) -> str:
        """
        Chat with additional injected context (e.g. PDF content, weather data).
        The extra_context is prepended to the user message.
        Fact extraction runs only on the real user_message, never on
        injected external content (news/weather/PDF text can contain
        false-positive name/location patterns).
        """
        if self.memory:
            self.memory.extract_and_store_facts(user_message)
        augmented = f"{extra_context}\n\nUser question: {user_message}"
        return self.chat(augmented, extract_facts=False)

    # ─── Message Building ─────────────────────────────────────────────────────

    def _build_messages(self, user_message: str) -> List[Dict]:
        """Build the full message list for the API call."""
        messages = []

        # System prompt (personality)
        system_prompt = config.PERSONALITY_PROMPTS.get(
            self._personality,
            config.PERSONALITY_PROMPTS["default"],
        )

        # Append memory context to system prompt
        if self.memory:
            ctx = self.memory.get_context_prompt()
            if ctx:
                system_prompt += f"\n\n{ctx}"

        messages.append({"role": "system", "content": system_prompt})

        # Conversation history
        if self.memory:
            messages.extend(self.memory.get_messages_for_llm())

        # Current user message
        messages.append({"role": "user", "content": user_message})

        return messages

    # ─── Streaming ───────────────────────────────────────────────────────────

    def chat_stream(self, user_message: str):
        """
        Generator that yields response tokens as they arrive.
        Useful for printing/speaking progressively.
        """
        messages = self._build_messages(user_message)
        full_reply = []

        try:
            with requests.post(
                f"{self._base_url}/api/chat",
                json={
                    "model": self._model,
                    "messages": messages,
                    "stream": True,
                    "options": {"temperature": config.LLM_TEMPERATURE},
                },
                timeout=config.OLLAMA_TIMEOUT,
                stream=True,
            ) as resp:
                for line in resp.iter_lines():
                    if line:
                        chunk = json.loads(line)
                        token = chunk.get("message", {}).get("content", "")
                        if token:
                            full_reply.append(token)
                            yield token
                        if chunk.get("done"):
                            break

        except Exception as e:
            log.error(f"Stream error: {e}")
            yield "I encountered an error."

        # Save to memory after stream completes
        if self.memory and full_reply:
            self.memory.add_exchange(user_message, "".join(full_reply))

    # ─── Intent Classification ────────────────────────────────────────────────

    def classify_intent(self, user_message: str) -> dict:
        """
        Ask the LLM to classify the user's intent.
        Returns {"intent": str, "target": str, "confidence": float}
        """
        classify_prompt = f"""Classify this voice command into one of these intents:
open_app, close_app, weather, summarize_pdf, general_question,
set_reminder, search_web, system_command, personal_question, chitchat

Command: "{user_message}"

Respond ONLY with valid JSON in this exact format:
{{"intent": "intent_name", "target": "extracted_target_or_empty_string"}}

Examples:
Examples:
"Open Spotify" → {{"intent": "open_app", "target": "Spotify"}}
"What's the weather in London?" → {{"intent": "weather", "target": "London"}}
"Summarize my resume PDF" → {{"intent": "summarize_pdf", "target": "resume"}}
"Tell me a joke" → {{"intent": "chitchat", "target": ""}}
"What time is it?" → {{"intent": "system_command", "target": "time"}}
"Turn up the volume" → {{"intent": "system_command", "target": "volume_up"}}
"Take a screenshot" → {{"intent": "system_command", "target": "screenshot"}}"""
        try:
            resp = requests.post(
                f"{self._base_url}/api/generate",
                json={
                    "model": self._model,
                    "prompt": classify_prompt,
                    "stream": False,
                    "format": "json",
                    "options": {"temperature": 0.1, "num_predict": 80},
                },
                timeout=15,
            )
            result = json.loads(resp.json()["response"])
            log.debug(f"Intent classified: {result}")
            return result

        except Exception as e:
            log.warning(f"Intent classification failed: {e}. Defaulting to general_question.")
            return {"intent": "general_question", "target": ""}

    # ─── Personality Control ──────────────────────────────────────────────────

    def set_personality(self, mode: str):
        """Switch personality mode at runtime."""
        if mode in config.PERSONALITY_PROMPTS:
            self._personality = mode
            log.info(f"Personality changed to: {mode}")
        else:
            log.warning(f"Unknown personality: {mode}")

    def get_personality(self) -> str:
        return self._personality

    # ─── Model Management ────────────────────────────────────────────────────

    def list_available_models(self) -> list[str]:
        """Return list of models pulled in Ollama."""
        try:
            resp = requests.get(f"{self._base_url}/api/tags", timeout=3)
            return [m["name"] for m in resp.json().get("models", [])]
        except Exception:
            return []

    def switch_model(self, model_name: str):
        """Switch to a different local model."""
        self._model = model_name
        log.info(f"Switched to model: {model_name}")
