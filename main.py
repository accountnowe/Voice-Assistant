"""
JARVIS — Local AI Assistant
============================
Entry point for the JARVIS assistant.

Architecture:
  Microphone → Wake Word → STT → LLM (Ollama) → Action Router → TTS → Speaker

Quick Start:
  1. Install dependencies:   pip install -r requirements.txt
  2. Install Ollama:          https://ollama.ai
  3. Pull a model:            ollama pull mistral
  4. Run:                     python main.py

Flags:
  python main.py --no-wake     Skip wake-word; press Enter to speak
  python main.py --text        Text-only mode (no microphone)
  python main.py --model phi3  Override LLM model
  python main.py --personality funny  Set personality at launch
"""

import sys
import time
import signal
import argparse
import threading
from utils.logger import get_logger
from gui import JarvisGUI

log = get_logger("main")

# ─── Startup Banner ───────────────────────────────────────────────────────────




def print_banner():
    
    print("  Initializing components...\n")


# ─── Argument Parsing ─────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(description="JARVIS Local AI Assistant")
    parser.add_argument("--no-wake", action="store_true",
                        help="Skip wake word; press Enter to activate")
    parser.add_argument("--text", action="store_true",
                        help="Text-only mode (no mic/speaker)")
    parser.add_argument("--model", type=str, default=None,
                        help="Override Ollama model (e.g. phi3, llama3.2)")
    parser.add_argument("--personality", type=str, default=None,
                        choices=["default", "formal", "funny", "sarcastic"],
                        help="Set personality mode")
    parser.add_argument("--debug", action="store_true",
                        help="Enable debug logging")
    return parser.parse_args()


# ─── JARVIS Core ──────────────────────────────────────────────────────────────

class JARVIS:
    """Main assistant orchestrator."""

    def __init__(self, args, gui=None):
        self.args = args
        self.gui = gui
        self.running = False
        self.always_listening = False
        self._setup_signal_handlers()

        # Apply overrides
        import config
        if args.debug:
            config.DEBUG_MODE = True
            config.LOG_LEVEL = "DEBUG"
        if args.model:
            config.OLLAMA_MODEL = args.model
        if args.personality:
            config.PERSONALITY_MODE = args.personality

        # Initialize components
        print("  [1/5] Loading memory system...")
        from brain.memory import Memory
        self.memory = Memory()

        print("  [2/5] Connecting to LLM (Ollama)...")
        from brain.llm import LLM
        self.llm = LLM(memory=self.memory)

        if not args.text:
            print("  [3/5] Loading Speech-to-Text...")
            from audio.stt import STT
            self.stt = STT()

            print("  [4/5] Loading Text-to-Speech...")
            from audio.tts import TTS
            self.tts = TTS(gui=self.gui)
        else:
            self.stt = None
            self.tts = MockTTS()

        print("  [5/5] Initializing action router...")
        from actions.router import ActionRouter
        self.router = ActionRouter(
            llm=self.llm,
            tts=self.tts,
            memory=self.memory,
        )

        print("\n  ✓ JARVIS is ready!\n")

        # Greet user
        user_name = self.memory.recall("user_name")
        greeting = f"Hello{', ' + user_name if user_name else ''}! JARVIS online. How can I help?"
        self.tts.speak(greeting)

    # ─── Main Loop ────────────────────────────────────────────────────────────

    def run(self):
        """Start the main assistant loop."""
        self.running = True

        if self.args.text:
            self._run_text_loop()
        elif self.args.no_wake:
            self._run_push_to_talk_loop()
        else:
            self._run_voice_loop()

    def _run_voice_loop(self):
        """
        Full voice loop with wake-word detection.
        Runs wake-word detector in background thread.
        """
        from audio.wake_word import WakeWordDetector

        log.info("Starting wake-word detection loop...")
        print(f"  Waiting for wake word: '{__import__('config').WAKE_WORD}'")
        print("  (Press Ctrl+C to quit)\n")

        detector = WakeWordDetector()

        try:
            detector.listen(callback=self._on_wake)
        except KeyboardInterrupt:
            self._shutdown()

    def _run_push_to_talk_loop(self):
        """No wake-word: press Enter to speak."""
        log.info("Push-to-talk mode active")
        print("  Press Enter to speak, Ctrl+C to quit\n")

        while self.running:
            try:
                input("  [Press Enter to speak] ")
                self._listen_and_respond()
            except KeyboardInterrupt:
                break
            except EOFError:
                break

        self._shutdown()

    def _run_text_loop(self):
        """Text-only mode for testing."""
        log.info("Text mode active")
        print("  Type your message, 'quit' to exit\n")

        while self.running:
            try:
                user_input = input("  You: ").strip()
                if not user_input:
                    continue
                if user_input.lower() in ["quit", "exit", "bye"]:
                    break

                print("  JARVIS: ", end="", flush=True)
                response = self.router.handle(user_input)
                if response == "__EXIT__":
                    break
                print(response)
                print()

            except KeyboardInterrupt:
                break
            except EOFError:
                break

        self._shutdown()

    # ─── Wake Word Callback ────────────────────────────────────────────────────

    def _on_wake(self):
        """Called when wake word is detected."""
        log.info("Wake word triggered!")

        # Play acknowledgment sound / chime (optional)
        self._play_chime()

        # Listen and respond
        self._listen_and_respond()

        # If always-listening was just turned on, keep listening directly
        # without requiring the wake word again, until turned off
        while self.always_listening:
            self._listen_and_respond()

    def _listen_and_respond(self, auto_process: bool = True):
        """
        Listen for user speech, process it, respond.
        auto_process=True (wake-word / --no-wake path): processes immediately.
        auto_process=False (GUI mic-button path): drops text into the input
        box for review/editing instead of processing right away.
        """
        if not self.stt:
            return

        # Short "listening" indicator
        print("\n  [Listening...]")
        if self.gui:
            self.gui.set_state("listening")

        text = self.stt.listen()

        if self.gui:
            self.gui.set_state("idle")

        if not text or len(text.strip()) < 2:
            log.info("No speech detected")
            return

        if not auto_process and self.gui:
            # GUI mic-button path — let the user review/edit before sending
            self.gui.set_input_text(text)
            return

        text_lower = text.lower()

        # Always-listening toggle — checked BEFORE normal routing so it
        # never collides with existing commands like "go to sleep" (laptop sleep)
        if "stay awake" in text_lower:
            self.always_listening = True
            response = "Staying awake. Just talk, no need to say Hey Jarvis."
            print(f"  You: {text}")
            print(f"  JARVIS: {response}")
            if self.gui:
                self.gui.add_message("You", text)
            self.tts.speak(response)
            return
        if "go to sleep mode" in text_lower or "wake word mode" in text_lower:
            self.always_listening = False
            response = "Back to wake-word mode. Say Hey Jarvis to talk to me."
            print(f"  You: {text}")
            print(f"  JARVIS: {response}")
            if self.gui:
                self.gui.add_message("You", text)
            self.tts.speak(response)
            return

        print(f"  You: {text}")
        if self.gui:
            self.gui.add_message("You", text)

        # Handle the command
        response = self.router.handle(text)

        if response == "__EXIT__":
            print("  JARVIS: Goodbye!")
            self.tts.speak("Goodbye! Shutting down.")
            self._shutdown()
            return

        print(f"  JARVIS: {response}\n")

    def _play_chime(self):
        """Play a short activation sound (macOS only)."""
        try:
            import subprocess
            import platform
            if platform.system() == "Darwin":
                # Use afplay with a system sound
                subprocess.Popen(
                    ["afplay", "/System/Library/Sounds/Tink.aiff"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
        except Exception:
            pass

    # ─── Shutdown ────────────────────────────────────────────────────────────

    def _shutdown(self):
        """Graceful shutdown."""
        log.info("Shutting down JARVIS...")
        self.running = False

        if hasattr(self, "memory"):
            self.memory.close()
        if hasattr(self, "tts"):
            self.tts.stop()

        print("\n  Goodbye. JARVIS offline.\n")
        sys.exit(0)

    def _setup_signal_handlers(self):
        """Handle Ctrl+C gracefully. Only works on the main thread — skip
        silently if JARVIS is running on a background thread (GUI mode)."""
        try:
            signal.signal(signal.SIGINT, lambda s, f: self._shutdown())
            signal.signal(signal.SIGTERM, lambda s, f: self._shutdown())
        except ValueError:
            log.info("Signal handlers skipped (not on main thread) — use Ctrl+C in terminal or close GUI window to exit")


# ─── Mock TTS (text mode) ─────────────────────────────────────────────────────

class MockTTS:
    """Silent TTS for text-only mode."""
    def speak(self, text): pass
    def speak_async(self, text): pass
    def stop(self): pass


# ─── Entry Point ──────────────────────────────────────────────────────────────

def main():
    print_banner()
    args = parse_args()

    gui = JarvisGUI()
    jarvis_holder = {}  # holds the JARVIS instance once created, so the GUI button can reach it

    def on_speak_button_clicked():
        jarvis = jarvis_holder.get("instance")
        if jarvis and not jarvis.stt is None:
            # GUI mic-button click → editable review path (auto_process=False)
            threading.Thread(target=jarvis._listen_and_respond, args=(False,), daemon=True).start()

    def on_text_submitted(text):
        jarvis = jarvis_holder.get("instance")
        if jarvis:
            def process():
                gui.add_message("You", text)
                response = jarvis.router.handle(text)
                if response == "__EXIT__":
                    jarvis._shutdown()
            threading.Thread(target=process, daemon=True).start()

    gui.on_speak_callback = on_speak_button_clicked
    gui.on_text_submit_callback = on_text_submitted

    def start_jarvis():
        try:
            jarvis = JARVIS(args, gui=gui)
            jarvis_holder["instance"] = jarvis
            jarvis.run()
        except KeyboardInterrupt:
            print("\n  Interrupted. Goodbye!\n")
        except Exception as e:
            log.error(f"Fatal error: {e}", exc_info=True)
            print(f"\n  Fatal error: {e}")
            print("  Check logs/ for details.\n")

    threading.Thread(target=start_jarvis, daemon=True).start()
    gui.run()  # blocks on main thread — required by Tkinter


if __name__ == "__main__":
    main()
