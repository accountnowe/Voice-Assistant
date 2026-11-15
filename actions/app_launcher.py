"""
JARVIS App Launcher
===================
Open and close applications on macOS and Windows.

macOS: Uses `open -a "App Name"` and `osascript`
Windows: Uses `subprocess.Popen` with Win32 app paths

Usage:
    launcher = AppLauncher()
    success, msg = launcher.open_app("Spotify")
    success, msg = launcher.close_app("Spotify")
"""

import os
import time
import platform
import subprocess
from utils.logger import get_logger

log = get_logger("app_launcher")
PLATFORM = platform.system()


class AppLauncher:
    """Cross-platform application launcher."""

    # ─── Open ────────────────────────────────────────────────────────────────

    def open_app(self, app_name: str) -> tuple[bool, str]:
        """
        Launch an application by name.
        Returns (success: bool, message: str)
        """
        log.info(f"Opening app: {app_name}")

        if PLATFORM == "Darwin":
            return self._open_macos(app_name)
        elif PLATFORM == "Windows":
            return self._open_windows(app_name)
        else:
            return self._open_linux(app_name)

    def _open_macos(self, app_name: str) -> tuple[bool, str]:
        """Open app on macOS using `open -a`."""
        try:
            result = subprocess.run(
                ["open", "-a", app_name],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return True, f"Opening {app_name}."
            else:
                # Try with .app extension
                result2 = subprocess.run(
                    ["open", "-a", f"{app_name}.app"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if result2.returncode == 0:
                    return True, f"Opening {app_name}."
                return False, f"I couldn't find {app_name}. Is it installed?"
        except subprocess.TimeoutExpired:
            return False, f"Timed out trying to open {app_name}."
        except FileNotFoundError:
            return False, "The open command is not available."

    def _open_windows(self, app_name: str) -> tuple[bool, str]:
        """Open app on Windows using os.startfile (verifies launch actually succeeds)."""
        # Special system apps that aren't launched by name — they use URI schemes
        special_apps = {
            "settings": "ms-settings:",
            "windows settings": "ms-settings:",
            "control panel": "control",
            "file explorer": "explorer",
            "explorer": "explorer",
            "command prompt": "cmd",
            "cmd": "cmd",
        }

        key = app_name.lower().strip()
        if key in special_apps:
            try:
                os.startfile(special_apps[key])
                return True, f"Opening {app_name}."
            except OSError as e:
                log.warning(f"Failed to open special app {app_name}: {e}")
                return False, f"I couldn't open {app_name}."

        # Common Windows app locations (fallback search)
        search_paths = [
            r"C:\Program Files",
            r"C:\Program Files (x86)",
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs"),
            os.path.join(os.environ.get("APPDATA", ""), "Microsoft\Windows\Start Menu\Programs"),
        ]

        # Direct launch — os.startfile raises OSError if it genuinely can't find/run it
        for attempt in [app_name, app_name.lower(), app_name.replace(" ", "")]:
            try:
                os.startfile(attempt)
                return True, f"Opening {app_name}."
            except OSError:
                continue

        # Search for .exe in common paths
        app_exe = app_name.replace(" ", "") + ".exe"
        for base in search_paths:
            for root, dirs, files in os.walk(base):
                for f in files:
                    if f.lower() == app_exe.lower():
                        try:
                            os.startfile(os.path.join(root, f))
                            return True, f"Opening {app_name}."
                        except OSError as e:
                            log.warning(f"Found but couldn't open {f}: {e}")

        return False, f"I couldn't find {app_name}. Is it installed?"

    def _open_linux(self, app_name: str) -> tuple[bool, str]:
        """Open app on Linux."""
        for attempt in [app_name.lower(), app_name.lower().replace(" ", "-"),
                         app_name.lower().replace(" ", "")]:
            try:
                subprocess.Popen(
                    [attempt],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return True, f"Opening {app_name}."
            except FileNotFoundError:
                pass
        return False, f"I couldn't find {app_name}."

    # ─── Close ───────────────────────────────────────────────────────────────

    def close_app(self, app_name: str) -> tuple[bool, str]:
        """Gracefully close an application."""
        log.info(f"Closing app: {app_name}")

        if PLATFORM == "Darwin":
            return self._close_macos(app_name)
        elif PLATFORM == "Windows":
            return self._close_windows(app_name)
        else:
            return self._close_linux(app_name)

    def _close_macos(self, app_name: str) -> tuple[bool, str]:
        """Use AppleScript to quit app gracefully."""
        script = f'tell application "{app_name}" to quit'
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            return True, f"Closing {app_name}."
        # Fallback to pkill
        result2 = subprocess.run(
            ["pkill", "-f", app_name],
            capture_output=True, text=True
        )
        if result2.returncode == 0:
            return True, f"Closed {app_name}."
        return False, f"I couldn't close {app_name}. It may not be running."

    def _close_windows(self, app_name: str) -> tuple[bool, str]:
        app_exe = app_name.replace(" ", "") + ".exe"
        result = subprocess.run(
            ["taskkill", "/F", "/IM", app_exe],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            return True, f"Closed {app_name}."
        return False, f"I couldn't find {app_name} running."

    def _close_linux(self, app_name: str) -> tuple[bool, str]:
        result = subprocess.run(
            ["pkill", "-f", app_name],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            return True, f"Closed {app_name}."
        return False, f"I couldn't find {app_name} running."

    # ─── Utility ─────────────────────────────────────────────────────────────

    def is_running(self, app_name: str) -> bool:
        """Check if an app is currently running."""
        if PLATFORM == "Darwin":
            result = subprocess.run(
                ["pgrep", "-f", app_name],
                capture_output=True
            )
            return result.returncode == 0
        elif PLATFORM == "Windows":
            result = subprocess.run(
                ["tasklist", "/FI", f"IMAGENAME eq {app_name}.exe"],
                capture_output=True, text=True
            )
            return app_name.lower() in result.stdout.lower()
        return False

    def list_running_apps(self) -> list[str]:
        """Return list of currently running application names."""
        if PLATFORM == "Darwin":
            script = 'tell application "System Events" to get name of every process whose background only is false'
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                return [a.strip() for a in result.stdout.split(",")]
        elif PLATFORM == "Windows":
            result = subprocess.run(
                ["tasklist", "/FO", "CSV", "/NH"],
                capture_output=True, text=True
            )
            lines = result.stdout.strip().split("\n")
            return [l.split(",")[0].strip('"').replace(".exe", "") for l in lines if l]
        return []
