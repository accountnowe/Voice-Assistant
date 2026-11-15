"""
JARVIS Google Search
=====================
Opens a Google search results page for a given query.
Same pattern as youtube_search.py.

Usage:
    gs = GoogleSearch()
    success, msg = gs.search(query)
"""

import os
import urllib.parse
from utils.logger import get_logger

log = get_logger("google_search")


class GoogleSearch:
    """Opens Google search results in the default browser."""

    def search(self, query: str) -> tuple[bool, str]:
        """
        Open a Google search for the given query.
        Returns (success: bool, message: str)
        """
        if not query or not query.strip():
            return False, "I didn't catch what you wanted to search for."

        try:
            encoded_query = urllib.parse.quote_plus(query.strip())
            url = f"https://www.google.com/search?q={encoded_query}"
            os.startfile(url)
            log.info(f"Opened Google search for: {query}")
            return True, f"Searching Google for {query}."
        except OSError as e:
            log.error(f"Failed to open Google search: {e}")
            return False, f"I couldn't open Google for {query}."