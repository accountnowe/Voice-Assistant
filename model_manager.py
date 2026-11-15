"""
Model manager: checks/starts Ollama and downloads models through
Ollama's own API. Nothing is bundled with the app.
"""

import json
import shutil
import subprocess
import time
import requests
import config

HOST = config.OLLAMA_HOST


def ollama_installed() -> bool:
    return shutil.which("ollama") is not None


def ollama_running() -> bool:
    try:
        requests.get(f"{HOST}/api/tags", timeout=2)
        return True
    except requests.exceptions.RequestException:
        return False


def start_ollama(wait_seconds: int = 20) -> bool:
    """Start the Ollama server in the background (no window) if needed."""
    if ollama_running():
        return True
    if not ollama_installed():
        return False
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)  # Windows only
    subprocess.Popen(
        ["ollama", "serve"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=flags,
    )
    for _ in range(wait_seconds):
        time.sleep(1)
        if ollama_running():
            return True
    return False


def installed_models() -> list:
    try:
        r = requests.get(f"{HOST}/api/tags", timeout=3)
        return [m["name"] for m in r.json().get("models", [])]
    except requests.exceptions.RequestException:
        return []


def has_model(name: str) -> bool:
    if ":" not in name:
        name += ":latest"
    return name in installed_models()


def pull_model(name: str, on_progress=print) -> bool:
    """Download a model via Ollama, reporting progress lines to on_progress."""
    try:
        with requests.post(
            f"{HOST}/api/pull",
            json={"model": name, "stream": True},
            stream=True,
            timeout=(5, None),
        ) as r:
            r.raise_for_status()
            for line in r.iter_lines():
                if not line:
                    continue
                data = json.loads(line)
                if "error" in data:
                    on_progress(f"Error: {data['error']}")
                    return False
                status = data.get("status", "")
                total, done = data.get("total"), data.get("completed")
                if total and done is not None:
                    on_progress(f"{status}: {done * 100 // total}%")
                else:
                    on_progress(status)
                if status == "success":
                    return True
    except requests.exceptions.RequestException as e:
        on_progress(f"Download failed: {e}")
    return False