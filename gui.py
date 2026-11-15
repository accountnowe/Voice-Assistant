"""
JARVIS GUI
==========
Visual interface: a scrolling text log of the conversation, plus an
animated waveform (vertical bars) that reacts to state:
  - Idle     : flat, dim gray bars
  - Listening: gentle blue animated bars
  - Speaking : lively green animated bars

Runs on the main thread (Tkinter requirement). The voice loop runs
on a background thread and calls into this GUI via thread-safe
`root.after()` scheduling.

Standalone test:
    python gui.py
"""

import tkinter as tk
import customtkinter as ctk
import threading
import random
import time


class JarvisGUI:
    COLORS = {
        "idle": "#3a3a3a",
        "listening": "#2d7dd2",
        "speaking": "#2ecc71",
    }

    NUM_BARS = 12
    BAR_WIDTH = 18
    BAR_GAP = 10
    CANVAS_HEIGHT = 140
    BASE_BAR_HEIGHT = 6

    def __init__(self):
        ctk.set_appearance_mode("dark")
        self.root = ctk.CTk()
        self.root.title("JARVIS")
        self.root.configure(fg_color="#0f0f0f")
        self.root.after(10, lambda: self.root.state("zoomed"))  # delay ensures it applies after window is drawn

        # ── Waveform canvas ──────────────────────────────────────────────
        canvas_width = self.NUM_BARS * (self.BAR_WIDTH + self.BAR_GAP)
        self.canvas = tk.Canvas(
            self.root, width=420, height=self.CANVAS_HEIGHT,
            bg="#0f0f0f", highlightthickness=0
        )
        self.canvas.pack(pady=(25, 15))

        start_x = (420 - canvas_width) // 2
        center_y = self.CANVAS_HEIGHT // 2
        self.bars = []
        self._bar_heights = []
        for i in range(self.NUM_BARS):
            x = start_x + i * (self.BAR_WIDTH + self.BAR_GAP)
            bar = self.canvas.create_rectangle(
                x, center_y - self.BASE_BAR_HEIGHT // 2,
                x + self.BAR_WIDTH, center_y + self.BASE_BAR_HEIGHT // 2,
                fill=self.COLORS["idle"], outline=""
            )
            self.bars.append(bar)
            self._bar_heights.append(self.BASE_BAR_HEIGHT)

        # ── Text input row (mic button + entry + send, all in one row) ────
        self.on_speak_callback = None       # set from main.py
        self.on_text_submit_callback = None  # set from main.py
        input_frame = tk.Frame(self.root, bg="#0f0f0f")
        input_frame.pack(side="bottom", fill="x", padx=15, pady=10)

        self.input_entry = tk.Entry(
            input_frame, font=("Segoe UI", 11), bg="#1e1e1e", fg="#e0e0e0",
            insertbackground="#e0e0e0", relief="flat"
        )
        self.input_entry.pack(side="left", fill="x", expand=True, ipady=8, padx=(0, 8))
        self.input_entry.bind("<Return>", self._on_text_enter)

        self.send_button = ctk.CTkButton(
            input_frame, text="↑", font=("Segoe UI", 28, "bold"),
            fg_color="#3a3a3a", hover_color="#4a4a4a", text_color="white",
            corner_radius=20, width=44, height=44,
            command=self._on_text_enter
        )
        self.send_button.pack(side="right")

        self.speak_button = ctk.CTkButton(
            input_frame, text="🎙", font=("Segoe UI", 16),
            fg_color="#3a3a3a", hover_color="#4a4a4a", text_color="white",
            corner_radius=20, width=44, height=44,
            command=self._on_speak_click
        )
        self.speak_button.pack(side="right", padx=(0, 8))

        # ── Conversation log ──────────────────────────────────────────────
        self.text = tk.Text(
            self.root, bg="#111111", fg="#e0e0e0", wrap="word",
            font=("Segoe UI", 19), state="disabled", padx=12, pady=12,
            relief="flat"
        )
        self.text.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        self._state = "idle"
        self._animate()

    def _animate(self):
        """Waveform animation loop, runs continuously via root.after."""
        center_y = self.CANVAS_HEIGHT // 2
        color = self.COLORS.get(self._state, self.COLORS["idle"])

        for i, bar in enumerate(self.bars):
            if self._state == "idle":
                target_h = self.BASE_BAR_HEIGHT
            elif self._state == "listening":
                target_h = random.randint(10, 45)
            else:  # speaking — livelier
                target_h = random.randint(15, 90)

            # Smooth toward target instead of snapping
            current = self._bar_heights[i]
            new_h = current + (target_h - current) * 0.4
            self._bar_heights[i] = new_h

            x = self.canvas.coords(bar)[0]
            self.canvas.coords(
                bar,
                x, center_y - new_h / 2,
                x + self.BAR_WIDTH, center_y + new_h / 2
            )
            self.canvas.itemconfig(bar, fill=color)

        delay = 60 if self._state != "speaking" else 40
        self.root.after(delay, self._animate)

    # ── Thread-safe public methods ──────────────────────────────────────

    def _on_speak_click(self):
        if self.on_speak_callback:
            self.on_speak_callback()

    def _on_text_enter(self, event=None):
        text = self.input_entry.get().strip()
        if not text:
            return
        self.input_entry.delete(0, "end")
        if self.on_text_submit_callback:
            self.on_text_submit_callback(text)

    def set_state(self, state: str):
        """state: 'idle' | 'listening' | 'speaking'. Safe to call from any thread."""
        self.root.after(0, lambda: setattr(self, "_state", state))

    def set_input_text(self, text: str):
        """Place text into the input box for review/editing, without submitting it."""
        def _fill():
            self.input_entry.delete(0, "end")
            self.input_entry.insert(0, text)
            self.input_entry.focus_set()
        self.root.after(0, _fill)

    def add_message(self, sender: str, message: str):
        """Append a line to the conversation log. Safe to call from any thread."""
        def _append():
            self.text.config(state="normal")
            self.text.insert("end", f"{sender}: {message}\n\n")
            self.text.see("end")
            self.text.config(state="disabled")
        self.root.after(0, _append)

    def run(self):
        """Blocking call — must run on the main thread."""
        self.root.mainloop()


# ── Standalone test ──────────────────────────────────────────────────────
if __name__ == "__main__":
    gui = JarvisGUI()

    def fake_activity():
        """Simulates a conversation to test the animation, on a background thread."""
        time.sleep(1)
        gui.set_state("listening")
        gui.add_message("You", "What's the weather?")
        time.sleep(3)
        gui.set_state("speaking")
        gui.add_message("JARVIS", "It's sunny and 75 degrees.")
        time.sleep(3)
        gui.set_state("idle")

    threading.Thread(target=fake_activity, daemon=True).start()
    gui.run()