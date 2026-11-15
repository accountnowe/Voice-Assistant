# 🤖 JARVIS — Offline-First AI Voice Assistant

**A private, locally powered voice assistant for Windows. Your voice, your machine, your control.**

JARVIS is an AI-powered desktop voice assistant designed to run locally on your Windows computer. It combines speech recognition, local language models, persistent memory, and system automation to help you interact with your PC using natural language.

No cloud-based AI subscription or API key is required for its core assistant functionality.

## ✨ Features

### 🎙️ Voice Interaction
- Wake-word activation
- Push-to-talk mode
- Local speech-to-text using Whisper
- Text-to-speech responses
- Keyboard input as an alternative to voice
- Editable speech transcripts

### 🧠 Local AI and Memory
- Local language model integration through Ollama
- Persistent conversation memory using SQLite
- Context-aware responses
- Configurable assistant personalities
- Intent recognition for natural-language commands

### ⚡ Windows Automation
- Launch applications
- Open websites
- Search for files and folders
- Read and work with PDF documents
- Control system volume and brightness
- Lock or shut down the computer
- Access system information
- Play music and perform supported web actions

### 🌦️ Online Information
- Weather information
- Web searches
- News-related queries
- YouTube and Google integration

*Internet access is required for online information and web-based features.*

### 🖥️ Desktop Interface
- Animated audio waveform
- Conversation history
- Microphone and keyboard controls
- Transcript editing
- Dark-themed interface
- Voice and text interaction

## 🔧 How It Works

JARVIS processes voice commands through a local assistant pipeline:

1. **Wake Word:** Detects when the assistant is being addressed.
2. **Speech Recognition:** Converts spoken input into text.
3. **Command Processing:** Identifies the requested action.
4. **Execution:** Runs the appropriate system action or assistant task.
5. **AI Response:** Uses the local language model to generate a response when needed.
6. **Voice Output:** Delivers the response through speech and the desktop interface.

## 💻 System Requirements

- Windows 10 or Windows 11
- Python 3.11 recommended
- Microphone and speakers
- Ollama installed for local AI functionality
- RAM and GPU resources appropriate for your selected language model

JARVIS is designed with resource-conscious local model options in mind. Actual performance depends on your hardware and selected model.

## 🚀 Getting Started

### 1. Install the prerequisites

Install:

- [Python](https://www.python.org/)
- [Git](https://git-scm.com/)
- [Ollama](https://ollama.com/)

### 2. Clone the repository

```bash
git clone https://github.com/accountnowe/Voice-Assistant.git
cd Voice-Assistant
```

### 3. Create a virtual environment

```bash
python -m venv venv
venv\Scripts\activate
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Download a local model

Install a model supported by your hardware using Ollama. For example:

```bash
ollama pull llama3.2:3b
```

### 6. Start JARVIS

```bash
python main.py
```

You can also use the included Windows setup script if applicable:

```bash
setup_windows.bat
```

## 🗣️ Example Commands

Try asking JARVIS to:

- "Open Chrome."
- "What is the weather today?"
- "Search for Python tutorials."
- "Find a PDF in my documents."
- "Turn the volume down."
- "What time is it?"
- "Lock my computer."
- "Remember this for later."

Available commands depend on the configured modules and integrations.

## 🔒 Privacy

JARVIS is designed around local processing:

- Voice recognition can run locally.
- Local language models handle AI responses.
- Conversation memory is stored locally using SQLite.
- Core assistant functionality does not require a cloud AI API.
- Online features connect to external services when requested.

Your local configuration and data should remain on your own computer. Avoid committing private credentials, environment files, databases, or personal logs to the repository.

## 🛠️ Built With

- **Python** — Core application
- **Ollama** — Local language models
- **Whisper** — Speech recognition
- **openWakeWord** — Wake-word detection
- **SQLite** — Persistent memory
- **Windows APIs** — Desktop and system automation

## 📌 Project Goals

- Make local AI assistants accessible on everyday Windows hardware.
- Keep core assistant functionality independent of cloud AI services.
- Combine voice interaction with practical desktop automation.
- Provide a customizable assistant with persistent memory.
- Keep the interface simple and responsive.

## 🤝 Contributions

Suggestions, bug reports, and improvements are welcome. Contributions should focus on reliability, privacy, usability, and expanding supported assistant capabilities.

---

**JARVIS — A smarter way to interact with your PC.**
