"""
JARVIS File Search
==================
Finds and opens files by name (any file type) in common locations:
Desktop, Downloads, Documents.

Usage:
    fs = FileSearch()
    success, msg = fs.find_and_open("resume")
"""

import os
import glob
import platform
from utils.logger import get_logger

log = get_logger("file_search")
PLATFORM = platform.system()


class FileSearch:
    """Find and open files by name across common folders."""

    SEARCH_DIRS = [
        os.path.expanduser("~/Desktop"),
        os.path.expanduser("~/Downloads"),
        os.path.expanduser("~/Documents"),
    ]

    def find_and_open(self, hint: str, only_type: str = None) -> tuple[bool, str]:
        """
        Search for a file or folder whose name contains `hint` (case-insensitive).
        only_type: None (either), "file", or "folder" — restricts the search
        to just that kind when specified.
        Returns (success: bool, message: str)
        """
        if not hint or not hint.strip():
            return False, "I didn't catch what you're looking for."

        hint_clean = hint.strip().lower()
        candidates = []

        for directory in self.SEARCH_DIRS:
            if not os.path.exists(directory):
                continue
            all_items = glob.glob(os.path.join(directory, "**", "*"), recursive=True)
            for item in all_items:
                if hint_clean not in os.path.basename(item).lower():
                    continue
                is_file = os.path.isfile(item)
                is_dir = os.path.isdir(item)
                if only_type == "file" and not is_file:
                    continue
                if only_type == "folder" and not is_dir:
                    continue
                if is_file or is_dir:
                    candidates.append(item)

        if not candidates:
            kind_label = f"{only_type} " if only_type else "file or folder "
            return False, f"I couldn't find a {kind_label}matching '{hint}' in your Desktop, Downloads, or Documents."

        # Most recently modified match wins
        candidates.sort(key=lambda p: os.path.getmtime(p), reverse=True)
        best_match = candidates[0]

        item_type = "folder" if os.path.isdir(best_match) else "file"
        try:
            os.startfile(best_match)
            log.info(f"Opened {item_type}: {best_match}")
            return True, f"Opening {os.path.basename(best_match)}."
        except OSError as e:
            log.error(f"Failed to open {best_match}: {e}")
            return False, f"I found the {item_type} {os.path.basename(best_match)} but couldn't open it."