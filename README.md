# 🤖 JARVIS: An Assistant with No Address

> *Offline-first AI voice assistant for Windows. Your voice, your machine, no cloud.*
---

## The Idea

Every time you speak to a cloud assistant, your voice leaves the room.
It travels to a server you will never see, is read by systems you did not choose, and comes back as an answer you were never really in control of.

**JARVIS was built to break that bargain.**

The mind behind it, a large language model, lives **on your own machine**. It hears you through your own microphone, thinks on your own graphics card, and answers through your own speakers. There is no subscription, no API bill, and no account to create. Your conversations, your memory, and your files stay with you.

And it does not just talk. **It acts.**

Say a sentence, and watch your computer obey: apps open, volume rises, a PDF is read and summarized, a forgotten file is found, a song begins to play, the screen locks.

It was designed to run on a modest laptop, one with **4 GB of VRAM and 8 GB of RAM**. No data-center hardware, no expensive GPU.

---

## What It Can Do

### 🎙️ Hear and Speak
- **Wake word**: say *"Hey Jarvis"* and it wakes (offline detection via openWakeWord)
- **Speech-to-text**: Whisper runs locally, so your voice is never uploaded
- **Spoken replies**: every answer is read aloud in a natural Windows voice
- **Three ways to talk**: wake word, push-to-talk, or plain typing

### 🧠 Think and Remember
- **Local LLM** through Ollama, with no cloud AI service involved
- **Persistent memory**: tell it your name once and it remembers next session (SQLite)
- **Four personalities**: default, formal, funny, sarcastic. Switch by voice: *"be funny"*
- **Context-aware answers**: live weather, search results, and PDF text are fed to the model so it answers from real data

### ⚡ Take Action
| Category | Examples |
|---|---|
| **Apps** | open Chrome, Word, Excel, VS Code, Firefox, Command Prompt, Settings |
| **Web** | search the web, latest news on a topic, search Google, play on YouTube |
| **Files** | find a file or folder by name, then open it |
| **Documents** | summarize any PDF from Desktop, Downloads, or Documents |
| **Weather** | live conditions for any city, with no API key |
| **Volume** | up, down, mute, unmute, or *"set volume to 60"* |
| **Brightness** | up, down, or *"set brightness to 40"* (laptop screens) |
| **Power** | lock, sleep, shut down (with a spoken-cancel safety window) |
| **Info** | time, date, battery, screenshots |

### 🖥️ A Real Interface
- Animated **waveform** that comes alive while it listens and speaks
- Live **conversation log**
- **Speak or type**: click the mic or use the keyboard
- **Review before sending**: your transcribed speech lands in the text box, so you can fix a misheard word and press Enter
- Fullscreen dark theme with rounded modern controls

---

## How It Works

```
 You speak ─► Wake word ─► Speech-to-Text ─► Router ─► Action ─► LLM ─► Voice + GUI
                                                │
                                      keyword check first
                                      (instant, no AI needed)
                                                │
                                      LLM intent classifier
                                      (only for open-ended requests)
```

The design idea that makes it fast and dependable: **don't ask the AI for things plain code can do better.** Common commands such as time, volume, power, and file search are caught by a keyword layer and executed instantly. The language model is reserved for what only it can do: understanding open-ended requests and putting real data into natural sentences.

---

## 🧩 Choosing the Model for Your Hardware

The best model is not the biggest one. It is the **biggest one your machine can run smoothly.** An oversized model spills into system RAM and disk, and a voice assistant that takes a minute to answer is not an assistant.

JARVIS was tuned on a laptop with an **NVIDIA GTX 1650 (4 GB VRAM) and ~7.5 GB RAM**, and the model that fits it is **Llama 3.2 (3B, ~2 GB)**. It loads fully into VRAM and typically answers in about 5 to 15 seconds.

| Your hardware | Recommended model | Pull command |
|---|---|---|
| ≤ 8 GB RAM, 4 GB VRAM (the reference laptop) | **Llama 3.2** ⭐ | `ollama pull llama3.2` |
| ≤ 8 GB RAM, no GPU | Llama 3.2 or Gemma 2 2B | `ollama pull gemma2:2b` |
| 16 GB RAM, 6 to 8 GB VRAM | Mistral 7B | `ollama pull mistral` |
| 16 GB+ RAM, 8 GB+ VRAM | Llama 3.1 8B | `ollama pull llama3.1:8b` |

Change the model in one line of `config.py`:

```python
OLLAMA_MODEL = "llama3.2"
```

---

## 🚀 Quick Start (Windows)

**Requirements:** Python 3.11, Git, [Ollama](https://ollama.com), a microphone.
Python 3.12 or older is recommended, because some audio packages do not yet ship prebuilt installers for the newest Python versions.

```bash
git clone <your-repo-url>
cd jarvis-ai-assistant

py -3.11 -m venv venv
venv\Scripts\activate

pip install -r requirements.txt
ollama pull llama3.2
```

Make sure Ollama is running (it usually starts on its own; otherwise run `ollama serve` in a separate terminal), then:

```bash
python main.py              # wake-word mode: say "Hey Jarvis"
python main.py --no-wake    # push-to-talk / GUI mic button
python main.py --text       # typing only, no microphone needed
```

> **Microphone tip:** if transcription looks like nonsense, turn off *"Enable audio enhancements"* in Windows Sound settings for your mic. Aggressive noise suppression can silence real speech.

---

## 🗣️ Command Cheat Sheet

```
Apps        open chrome · open word · open excel · open vs code · open command prompt
Weather     what's the weather in Jaipur
Web         search web for <query> · news on <topic> · search google for <query>
YouTube     play <song or video> · search youtube for <query>
PDF         summarize pdf <name or topic>
Files       find the file called <name> · find the folder called <name>
Volume      turn up the volume · set volume to 60 · mute · unmute
Brightness  brightness up · set brightness to 40
Power       lock screen · go to sleep · shut down the laptop · cancel shutdown
Info        what time is it · what's today · battery · take a screenshot
Mood        be formal · be funny · be sarcastic · normal mode
Memory      clear memory
```

---

## 🛠️ The Hard Parts

Anyone can chain a few APIs together. These were the problems that took real debugging:

- **Silent success**: the original launcher reported "Opening Chrome" even when nothing opened. Switching to `os.startfile` made failures real and detectable.
- **Small models and strict formats**: a compact LLM could not reliably classify simple commands. Instead of fighting the model, a keyword layer now handles them instantly.
- **Two worlds, one process**: a GUI must own the main thread, while a voice loop must never stop listening. They now run on separate threads and communicate through thread-safe scheduling.
- **A TTS engine that went mute**: speech synthesis silently stopped after the first reply on Windows. Fixed by running speech in a fresh process each time.
- **A dead dependency**: the search library was renamed, searches returned nothing, and the AI invented plausible answers to cover for it. A reminder that a *quiet* failure is worse than a loud one.
- **Windows has no single "control the laptop" API**: volume, brightness, and app launching each needed a different low-level interface.

---

## 🔒 Privacy

- Voice recognition, wake word, language model, memory, and speech all run on your machine
- Nothing is sent to any cloud AI service
- Memory is a local SQLite file
- Only features that fetch live public data use the internet: **weather, web/news search, and opening YouTube or Google**. Everything else works with Wi-Fi off.

---

## 🗺️ Roadmap

- [ ] Timers and clock-time alarms with spoken alerts
- [ ] Hands-free "stay awake" mode
- [ ] Screen understanding (vision model)
- [ ] Calendar integration
- [ ] System-tray mode and launch at startup
- [ ] Multi-language support

---



---

<div align="center">

**Your voice. Your machine. Your assistant.**

</div>
