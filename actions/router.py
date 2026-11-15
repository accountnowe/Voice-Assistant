from typing import Optional, List, Dict
"""
JARVIS Action Router
====================
Maps classified intents to action handlers.

Flow:
    user_text → LLM.classify_intent() → router.dispatch() → action handler → result
    result → LLM.chat_with_context() (if needed) → TTS

Usage:
    router = ActionRouter(llm, tts, memory)
    router.handle("Open Spotify")
    router.handle("What's the weather in Chicago?")
"""

from utils.logger import get_logger
import config

log = get_logger("router")


class ActionRouter:
    """Routes classified intents to appropriate action handlers."""

    def __init__(self, llm, tts, memory=None):
        self.llm = llm
        self.tts = tts
        self.memory = memory

        # Lazy-load action modules
        self._app_launcher = None
        self._pdf_reader = None
        self._weather = None
        self._web_search = None
        self._system = None

    # ─── Main Entry Point ────────────────────────────────────────────────────

    def handle(self, user_text: str) -> str:
        """
        Process user text end-to-end:
        classify intent → dispatch → generate response → speak it.
        Returns the spoken response string.
        """
        if not user_text or not user_text.strip():
            return ""

        log.info(f"Handling: '{user_text}'")

        # Check for hard-coded personality/control commands first
        control_response = self._check_control_commands(user_text)
        if control_response is not None:
            self.tts.speak(control_response)
            return control_response

        # Quick keyword pre-check — some models unreliably classify these
        # via LLM, so catch obvious cases before asking it
        system_keywords = [
            "what time", "what's the time", "current time", "what is the time",
            "tell me the time", "time right now", "time is it",
            "what day", "what's today", "today's date", "what is today",
            "what is the date", "tell me the date", "today's day",
            "current date", "current year", "what year",
            "volume up", "volume down", "turn up", "turn down",
            "volume to", "set volume",
            "mute", "unmute", "cancel shutdown",
            "lock screen", "lock the screen",
            "brightness", "screenshot", "battery", "set brightness",
            "open downloads", "open desktop", "open documents",
            "go to sleep", "sleep now",
            "shut down the laptop", "power off computer",
            "shut down the computer", "power off the laptop",
        ]
        play_keywords = ["play ", "put on ", "search youtube for "]
        news_keywords = ["news on", "news about", "latest news", "what's happening with"]
        file_keywords = [
            "file called", "file named", "find file", "find the file", "find a file",
            "search for file", "search for a file",
            "folder called", "folder named", "find folder", "find the folder", "find a folder",
            "search for folder", "search for a folder",
        ]
        google_keywords = ["search google for", "google search for", "search on google for"]
        pdf_keywords = ["summarize pdf", "summarize the pdf"]
        websearch_keywords = ["search web", "search the web"]

        t_lower = user_text.lower()
        if any(kw in t_lower for kw in system_keywords):
            intent, target = "system_command", user_text
            log.info(f"Matched system_command by keyword pre-check: '{user_text}'")
        elif any(kw in t_lower for kw in play_keywords):
            intent, target = "play_music", user_text
            log.info(f"Matched play_music by keyword pre-check: '{user_text}'")
        elif any(kw in t_lower for kw in news_keywords):
            intent, target = "news_search", user_text
            log.info(f"Matched news_search by keyword pre-check: '{user_text}'")
        elif any(kw in t_lower for kw in file_keywords):
            intent, target = "find_file", user_text
            log.info(f"Matched find_file by keyword pre-check: '{user_text}'")
        elif any(kw in t_lower for kw in google_keywords):
            intent, target = "google_search", user_text
            log.info(f"Matched google_search by keyword pre-check: '{user_text}'")
        elif any(kw in t_lower for kw in pdf_keywords):
            intent, target = "summarize_pdf", user_text
            log.info(f"Matched summarize_pdf by keyword pre-check: '{user_text}'")
        elif any(kw in t_lower for kw in websearch_keywords):
            intent, target = "search_web", user_text
            log.info(f"Matched search_web by keyword pre-check: '{user_text}'")
        else:
            # Classify intent via LLM
            intent_data = self.llm.classify_intent(user_text)
            intent = intent_data.get("intent", "general_question")
            target = intent_data.get("target", "")

        log.info(f"Intent: {intent}, Target: '{target}'")

        # Dispatch to handler
        response = self._dispatch(intent, target, user_text)

        # Speak the response
        if response:
            self.tts.speak(response)

        return response

    # ─── Control Commands ────────────────────────────────────────────────────

    def _check_control_commands(self, text: str) -> Optional[str]:
        """
        Handle meta-commands that don't need LLM classification.
        Returns response string if handled, None otherwise.
        """
        t = text.lower().strip()

        # Personality switches
        if any(p in t for p in ["be formal", "formal mode", "serious mode"]):
            self.llm.set_personality("formal")
            return "Switching to formal mode. How may I assist you?"

        if any(p in t for p in ["be funny", "funny mode", "joke mode", "be humorous"]):
            self.llm.set_personality("funny")
            return "Funny mode activated! Let's do this, shall we?"

        if any(p in t for p in ["be sarcastic", "sarcastic mode"]):
            self.llm.set_personality("sarcastic")
            return "Oh, great. Sarcastic mode. Because that's exactly what you needed."

        if any(p in t for p in ["normal mode", "default mode", "be normal"]):
            self.llm.set_personality("default")
            return "Back to normal. How can I help?"

        # Memory management
        if "clear memory" in t or "forget everything" in t:
            if self.memory:
                self.memory.clear_short_term()
            return "Short-term memory cleared. Starting fresh."

        # Stop/quit
        if t in ["stop", "quit", "exit", "goodbye", "bye jarvis", "shut down"]:
            return "__EXIT__"  # Signals main loop to stop

        return None

    # ─── Dispatcher ──────────────────────────────────────────────────────────

    def _dispatch(self, intent: str, target: str, user_text: str) -> str:
        handlers = {
            "open_app":          self._handle_open_app,
            "close_app":         self._handle_close_app,
            "weather":           self._handle_weather,
            "summarize_pdf":     self._handle_pdf,
            "search_web":        self._handle_web_search,
            "system_command":    self._handle_system,
            "play_music":        self._handle_play_music,
            "news_search":       self._handle_news_search,
            "find_file":         self._handle_find_file,
            "google_search":     self._handle_google_search,
            "general_question":  self._handle_general,
            "personal_question": self._handle_general,
            "chitchat":          self._handle_general,
            "set_reminder":      self._handle_reminder,
        }

        handler = handlers.get(intent, self._handle_general)
        try:
            return handler(target, user_text)
        except Exception as e:
            log.error(f"Handler error for intent '{intent}': {e}")
            return self.llm.chat(user_text)

    # ─── Handlers ────────────────────────────────────────────────────────────

    def _handle_open_app(self, target: str, user_text: str) -> str:
        launcher = self._get_launcher()
        app_name = self._resolve_app_name(target or user_text)
        success, message = launcher.open_app(app_name)
        if success:
            return message
        # Fall back to LLM if we can't find the app
        return self.llm.chat(user_text)

    def _handle_close_app(self, target: str, user_text: str) -> str:
        launcher = self._get_launcher()
        app_name = self._resolve_app_name(target or user_text)
        success, message = launcher.close_app(app_name)
        return message

    def _handle_weather(self, target: str, user_text: str) -> str:
        from actions.weather import WeatherAction
        if not self._weather:
            self._weather = WeatherAction()

        location = target or self._extract_location(user_text)
        data = self._weather.get_weather(location)

        if data:
            return self.llm.chat_with_context(
                user_text,
                f"Current weather data:\n{data}"
            )
        return "I couldn't fetch the weather right now. Please check your internet connection."

    def _handle_pdf(self, target: str, user_text: str) -> str:
        from actions.pdf_reader import PDFReader
        if not self._pdf_reader:
            self._pdf_reader = PDFReader()

        # Strip the trigger phrase to get just the filename/topic hint
        hint = user_text.lower()
        for trigger in ["summarize the pdf about", "summarize pdf about",
                        "summarize the pdf called", "summarize pdf called",
                        "summarize the pdf", "summarize pdf"]:
            if trigger in hint:
                hint = hint.split(trigger, 1)[1].strip()
                break

        # Try to find PDF file
        pdf_path = self._pdf_reader.find_recent_pdf(hint)
        if not pdf_path:
            return "I couldn't find a PDF to summarize. Please specify the file path or ask me to look in a specific folder."

        text = self._pdf_reader.extract_text(pdf_path)
        if not text:
            return f"I couldn't read text from {pdf_path}. The PDF might be image-based."

        # Summarize with LLM
        context = f"PDF file: {pdf_path}\n\nContent (truncated):\n{text[:config.PDF_CHUNK_SIZE]}"
        return self.llm.chat_with_context(
            "Please give a clear, concise summary of this PDF document.",
            context
        )

    def _handle_web_search(self, target: str, user_text: str) -> str:
        from actions.web_search import WebSearch
        if not self._web_search:
            self._web_search = WebSearch()

        query = target or user_text
        results = self._web_search.search(query)

        if results:
            return self.llm.chat_with_context(
                user_text,
                f"Web search results for '{query}':\n{results}"
            )
        return self.llm.chat(user_text)

    def _handle_system(self, target: str, user_text: str) -> str:
        from actions.system_commands import SystemCommands
        if not self._system:
            self._system = SystemCommands()

        result = self._system.execute(user_text)
        if result:
            return result
        return self.llm.chat(user_text)

    def _handle_play_music(self, target: str, user_text: str) -> str:
        from actions.youtube_search import YouTubeSearch
        yt = YouTubeSearch()

        # Strip the trigger word to get just the song/video/channel name
        query = user_text.lower()
        for trigger in ["play ", "put on ", "search youtube for "]:
            if trigger in query:
                query = query.split(trigger, 1)[1]
                break

        success, message = yt.play(query.strip())
        return message

    def _handle_news_search(self, target: str, user_text: str) -> str:
        from actions.web_search import WebSearch
        if not self._web_search:
            self._web_search = WebSearch()

        # Strip trigger phrase to get the actual topic
        query = user_text.lower()
        for trigger in ["news on", "news about", "latest news", "what's happening with"]:
            if trigger in query:
                query = query.split(trigger, 1)[1]
                break

        results = self._web_search.news_search(query.strip())
        if results:
            return self.llm.chat_with_context(user_text, f"News results:\n{results}")
        return "I couldn't find any news on that right now."

    def _handle_find_file(self, target: str, user_text: str) -> str:
        from actions.file_search import FileSearch
        fs = FileSearch()

        query = user_text.lower()
        # Detect whether the user specifically asked for a folder or a file
        wants_folder = "folder" in query
        wants_file = "file" in query and not wants_folder

        # Prefer splitting on "file called" / "folder called" etc — most reliable anchor
        for anchor in ["file called", "file named", "folder called", "folder named"]:
            if anchor in query:
                query = query.split(anchor, 1)[1]
                break
        else:
            # Fallback: strip common lead-in phrases
            for trigger in ["find the file", "find a file", "find file",
                            "search for file", "search for a file",
                            "find the folder", "find a folder", "find folder","find older",
                            "search for folder", "search for a folder"]:
                if trigger in query:
                    query = query.split(trigger, 1)[1]
                    break

        only_type = "folder" if wants_folder else ("file" if wants_file else None)
        clean_query = query.strip().rstrip(".,!?;:")
        success, message = fs.find_and_open(clean_query, only_type=only_type)
        return message

    def _handle_google_search(self, target: str, user_text: str) -> str:
        from actions.google_search import GoogleSearch
        gs = GoogleSearch()

        query = user_text.lower()
        for trigger in ["search google for", "google search for", "search on google for"]:
            if trigger in query:
                query = query.split(trigger, 1)[1]
                break

        success, message = gs.search(query.strip())
        return message

    def _handle_general(self, target: str, user_text: str) -> str:
        return self.llm.chat(user_text)

    def _handle_reminder(self, target: str, user_text: str) -> str:
        # Simple reminder using the LLM to acknowledge + memory to store
        if self.memory:
            self.memory.remember(
                f"reminder_{len(self.memory.get_all_facts())}",
                user_text,
                category="reminder"
            )
        return self.llm.chat(user_text)

    # ─── Helpers ─────────────────────────────────────────────────────────────

    def _get_launcher(self):
        if not self._app_launcher:
            from actions.app_launcher import AppLauncher
            self._app_launcher = AppLauncher()
        return self._app_launcher

    def _resolve_app_name(self, text: str) -> str:
        """Look up app alias, return canonical name."""
        t = text.lower().strip()
        return config.APP_ALIASES.get(t, text.title())

    def _extract_location(self, text: str) -> str:
        """Simple extraction of city/location from text."""
        import re
        patterns = [
            r"in ([A-Z][a-z]+(?: [A-Z][a-z]+)*)",
            r"for ([A-Z][a-z]+(?: [A-Z][a-z]+)*)",
        ]
        for p in patterns:
            m = re.search(p, text)
            if m:
                return m.group(1)
        return config.DEFAULT_LOCATION