from typing import Optional, List, Dict
"""
JARVIS System Commands
======================
Handle system-level voice commands like volume, brightness,
screen lock, file management, and more.

Usage:
    sys = SystemCommands()
    result = sys.execute("turn up the volume")
"""

import os
import re
import platform
import subprocess
from utils.logger import get_logger

log = get_logger("system_commands")
PLATFORM = platform.system()


class SystemCommands:
    """Platform-aware system command executor."""

    # ─── Command Dispatch ────────────────────────────────────────────────────

    def execute(self, command: str) -> Optional[str]:
        """
        Try to match command to a system action.
        Returns response string if handled, None if not recognized.
        """
        cmd = command.lower()

        # Volume — check for exact percentage first ("volume to 80", "set volume to 100")
        vol_match = re.search(r"(?:volume|set volume)(?:\s+to)?\s+(\d{1,3})", cmd)
        if vol_match:
            return self._volume_set(int(vol_match.group(1)))

        # Brightness — exact percentage ("brightness to 70", "set brightness to 50")
        bright_match = re.search(r"(?:brightness|set brightness)(?:\s+to)?\s+(\d{1,3})", cmd)
        if bright_match:
            return self._brightness_set(int(bright_match.group(1)))

        if any(x in cmd for x in ["volume up", "increase volume", "louder", "turn up"]):
            return self._volume_up()
        if any(x in cmd for x in ["volume down", "decrease volume", "quieter", "turn down"]):
            return self._volume_down()
        if "unmute" in cmd:
            return self._unmute()
        if "mute" in cmd:
            return self._mute()
        if "cancel shutdown" in cmd:
            return self._cancel_shutdown()

        # Screen
        if any(x in cmd for x in ["lock screen", "lock the screen", "lock computer"]):
            return self._lock_screen()
        if any(x in cmd for x in ["sleep", "go to sleep"]):
            return self._sleep()
        if any(x in cmd for x in ["shut down the laptop", "power off computer",
                                    "shut down the computer", "power off the laptop"]):
            return self._shutdown_laptop()
        if "brightness up" in cmd:
            return self._brightness_up()
        if "brightness down" in cmd:
            return self._brightness_down()
        if any(x in cmd for x in ["screenshot", "take a screenshot", "capture screen"]):
            return self._screenshot()

        # Files
        if any(x in cmd for x in ["open downloads", "show downloads"]):
            return self._open_folder("downloads")
        if any(x in cmd for x in ["open desktop", "show desktop"]):
            return self._open_folder("desktop")
        if any(x in cmd for x in ["open documents", "show documents"]):
            return self._open_folder("documents")

        # Date/Time
        if any(x in cmd for x in ["what time", "current time", "what's the time"]):
            from datetime import datetime
            now = datetime.now().strftime("%I:%M %p")
            return f"It's {now}."
        if any(x in cmd for x in ["what's today", "what day is it", "today's date"]):
            from datetime import datetime
            today = datetime.now().strftime("%A, %B %d, %Y")
            return f"Today is {today}."

        # Battery
        if any(x in cmd for x in ["battery", "how much battery"]):
            return self._battery_status()

        return None

    # ─── Volume ──────────────────────────────────────────────────────────────

    def _get_windows_volume_interface(self):
        """Get the Windows volume control interface (newer pycaw API)."""
        from pycaw.utils import AudioUtilities
        devices = AudioUtilities.GetSpeakers()
        return devices.EndpointVolume

    def _volume_set(self, percent: int) -> str:
        percent = max(0, min(100, percent))
        if PLATFORM == "Darwin":
            subprocess.run(
                ["osascript", "-e", f"set volume output volume {percent}"],
                capture_output=True
            )
        elif PLATFORM == "Windows":
            volume = self._get_windows_volume_interface()
            volume.SetMasterVolumeLevelScalar(percent / 100.0, None)
        return f"Volume set to {percent} percent."

    def _volume_up(self) -> str:
        if PLATFORM == "Darwin":
            subprocess.run(
                ["osascript", "-e", "set volume output volume (output volume of (get volume settings) + 10)"],
                capture_output=True
            )
        elif PLATFORM == "Windows":
            volume = self._get_windows_volume_interface()
            current = volume.GetMasterVolumeLevelScalar()
            volume.SetMasterVolumeLevelScalar(min(1.0, current + 0.1), None)
        return "Volume increased."

    def _volume_down(self) -> str:
        if PLATFORM == "Darwin":
            subprocess.run(
                ["osascript", "-e", "set volume output volume (output volume of (get volume settings) - 10)"],
                capture_output=True
            )
        elif PLATFORM == "Windows":
            volume = self._get_windows_volume_interface()
            current = volume.GetMasterVolumeLevelScalar()
            volume.SetMasterVolumeLevelScalar(max(0.0, current - 0.1), None)
        return "Volume decreased."

    def _mute(self) -> str:
        if PLATFORM == "Darwin":
            subprocess.run(
                ["osascript", "-e", "set volume with output muted"],
                capture_output=True
            )
        elif PLATFORM == "Windows":
            volume = self._get_windows_volume_interface()
            volume.SetMute(1, None)
        return "Muted."

    def _unmute(self) -> str:
        if PLATFORM == "Darwin":
            subprocess.run(
                ["osascript", "-e", "set volume without output muted"],
                capture_output=True
            )
        elif PLATFORM == "Windows":
            volume = self._get_windows_volume_interface()
            volume.SetMute(0, None)
        return "Unmuted."

    # ─── Brightness ──────────────────────────────────────────────────────────

    def _get_current_brightness_windows(self):
        """Get current brightness (0-100) via WMI. Laptop built-in screens only."""
        import wmi
        c = wmi.WMI(namespace="wmi")
        methods = c.WmiMonitorBrightness()[0]
        return methods.CurrentBrightness

    def _set_brightness_windows(self, percent: int):
        """Set brightness (0-100) via WMI. Laptop built-in screens only."""
        import wmi
        c = wmi.WMI(namespace="wmi")
        methods = c.WmiMonitorBrightnessMethods()[0]
        methods.WmiSetBrightness(percent, 0)

    def _brightness_set(self, percent: int) -> str:
        percent = max(0, min(100, percent))
        if PLATFORM == "Windows":
            try:
                self._set_brightness_windows(percent)
                return f"Brightness set to {percent} percent."
            except Exception as e:
                log.warning(f"Brightness control failed (likely external monitor): {e}")
                return "I couldn't adjust brightness — this usually only works on laptop built-in screens."
        return "Brightness control not implemented for this platform."

    def _brightness_up(self) -> str:
        if PLATFORM == "Darwin":
            subprocess.run(
                ["osascript", "-e", 'tell application "System Events" to key code 144'],
                capture_output=True
            )
            return "Brightness increased."
        elif PLATFORM == "Windows":
            try:
                current = self._get_current_brightness_windows()
                self._set_brightness_windows(min(100, current + 10))
                return "Brightness increased."
            except Exception as e:
                log.warning(f"Brightness control failed: {e}")
                return "I couldn't adjust brightness — this usually only works on laptop built-in screens."
        return "Brightness increased."

    def _brightness_down(self) -> str:
        if PLATFORM == "Darwin":
            subprocess.run(
                ["osascript", "-e", 'tell application "System Events" to key code 145'],
                capture_output=True
            )
            return "Brightness decreased."
        elif PLATFORM == "Windows":
            try:
                current = self._get_current_brightness_windows()
                self._set_brightness_windows(max(0, current - 10))
                return "Brightness decreased."
            except Exception as e:
                log.warning(f"Brightness control failed: {e}")
                return "I couldn't adjust brightness — this usually only works on laptop built-in screens."
        return "Brightness decreased."

    # ─── Screen ──────────────────────────────────────────────────────────────

    def _lock_screen(self) -> str:
        if PLATFORM == "Darwin":
            subprocess.run(
                ["osascript", "-e", 'tell application "System Events" to keystroke "q" using {command down, control down}'],
                capture_output=True
            )
        elif PLATFORM == "Windows":
            subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"])
        return "Screen locked."

    def _sleep(self) -> str:
        if PLATFORM == "Darwin":
            subprocess.run(["pmset", "sleepnow"], capture_output=True)
        elif PLATFORM == "Windows":
            subprocess.run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0", "1", "0"])
        return "Going to sleep."

    def _shutdown_laptop(self) -> str:
        """Shuts down the entire machine — gives a short warning first."""
        if PLATFORM == "Darwin":
            subprocess.run(["osascript", "-e", 'tell app "System Events" to shut down'])
        elif PLATFORM == "Windows":
            subprocess.run(["shutdown", "/s", "/t", "10"])
            return "Shutting down in 10 seconds. Say 'cancel shutdown' now to stop it."
        return "Shutting down."

    def _cancel_shutdown(self) -> str:
        if PLATFORM == "Windows":
            subprocess.run(["shutdown", "/a"])
            return "Shutdown cancelled."
        return "Cancel not supported on this platform."

    def _screenshot(self) -> str:
        if PLATFORM == "Darwin":
            import time
            filename = os.path.expanduser(
                f"~/Desktop/screenshot_{int(time.time())}.png"
            )
            subprocess.run(["screencapture", "-x", filename], capture_output=True)
            return f"Screenshot saved to Desktop."
        elif PLATFORM == "Windows":
            import time
            from PIL import ImageGrab
            filename = os.path.join(
                os.path.expanduser("~"), "Desktop",
                f"screenshot_{int(time.time())}.png"
            )
            ImageGrab.grab().save(filename)
            return f"Screenshot saved to Desktop."
        return "Screenshot not supported on this platform."

    # ─── Files ───────────────────────────────────────────────────────────────

    def _open_folder(self, folder_name: str) -> str:
        paths = {
            "downloads": os.path.expanduser("~/Downloads"),
            "desktop": os.path.expanduser("~/Desktop"),
            "documents": os.path.expanduser("~/Documents"),
        }
        path = paths.get(folder_name)
        if not path or not os.path.exists(path):
            return f"I couldn't find your {folder_name} folder."

        if PLATFORM == "Darwin":
            subprocess.run(["open", path], capture_output=True)
        elif PLATFORM == "Windows":
            subprocess.run(["explorer", path], capture_output=True)
        else:
            subprocess.run(["xdg-open", path], capture_output=True)

        return f"Opening your {folder_name} folder."

    # ─── Battery ─────────────────────────────────────────────────────────────

    def _battery_status(self) -> str:
        try:
            import psutil
            batt = psutil.sensors_battery()
            if batt:
                pct = int(batt.percent)
                plugged = "and charging" if batt.power_plugged else "on battery"
                return f"Battery is at {pct}% {plugged}."
        except ImportError:
            pass

        if PLATFORM == "Darwin":
            result = subprocess.run(
                ["pmset", "-g", "batt"],
                capture_output=True, text=True
            )
            return result.stdout.strip() or "Battery status unavailable."

        return "Battery information unavailable."