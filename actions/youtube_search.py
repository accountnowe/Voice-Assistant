"""
JARVIS YouTube Search
======================
Opens a YouTube search results page for a given query — songs, videos,
channels, anything. No API key needed, just a URL.

Usage:
    yt = YouTubeSearch()
    success, msg = yt.play(query)
"""

import os
import urllib.parse
from utils.logger import get_logger

log = get_logger("youtube_search")


class YouTubeSearch:
    """Opens YouTube search results in the default browser."""

    def play(self, query: str) -> tuple[bool, str]:
        """
        Open a YouTube search for the given query.
        Returns (success: bool, message: str)
        """
        if not query or not query.strip():
            return False, "I didn't catch what you wanted to play."

        try:
            encoded_query = urllib.parse.quote_plus(query.strip())
            url = f"https://www.youtube.com/results?search_query={encoded_query}"
            os.startfile(url)
            log.info(f"Opened YouTube search for: {query}")
            return True, f"Playing {query} on YouTube."
        except OSError as e:
            log.error(f"Failed to open YouTube search: {e}")
            return False, f"I couldn't open YouTube for {query}."