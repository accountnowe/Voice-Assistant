"""
JARVIS Web Search
=================
Search the web using DuckDuckGo — completely FREE, no API key needed.

Install: pip install duckduckgo-search

Usage:
    search = WebSearch()
    results = search.search("Python async programming")
"""

from utils.logger import get_logger

log = get_logger("web_search")


class WebSearch:
    """DuckDuckGo-powered web search (free, no API key)."""

    def search(self, query: str, max_results: int = 5) -> str:
        """
        Search DuckDuckGo and return formatted results as a string.
        Returns empty string on failure.
        """
        try:
            from ddgs import DDGS

            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))

            if not results:
                log.info(f"No results for: {query}")
                return ""

            lines = [f"Search results for: {query}", ""]
            for i, r in enumerate(results, 1):
                lines.append(f"{i}. {r.get('title', 'No title')}")
                lines.append(f"   {r.get('body', 'No description')}")
                lines.append(f"   URL: {r.get('href', 'N/A')}")
                lines.append("")

            text = "\n".join(lines)
            log.info(f"Found {len(results)} results for: {query}")
            return text

        except ImportError:
            log.error("duckduckgo-search not installed. Run: pip install duckduckgo-search")
            return ""
        except Exception as e:
            log.error(f"Search error: {e}")
            return ""

    def news_search(self, query: str, max_results: int = 5) -> str:
        """Search for recent news."""
        try:
            from ddgs import DDGS

            with DDGS() as ddgs:
                results = list(ddgs.news(query, max_results=max_results))

            if not results:
                return ""

            lines = [f"Latest news for: {query}", ""]
            for r in results:
                lines.append(f"• {r.get('title', '')}")
                lines.append(f"  {r.get('body', '')}")
                lines.append(f"  Source: {r.get('source', '')} | {r.get('date', '')}")
                lines.append("")

            return "\n".join(lines)

        except Exception as e:
            log.error(f"News search error: {e}")
            return ""
