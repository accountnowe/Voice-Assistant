from typing import Optional, List, Dict
"""

from typing import Optional, List, Dict
JARVIS PDF Reader
=================
Reads and extracts text from PDF files for summarization.

Install: pip install pymupdf
  (PyMuPDF is the fastest Python PDF library, handles complex layouts)

Usage:
    reader = PDFReader()
    text = reader.extract_text("/path/to/file.pdf")
    path = reader.find_recent_pdf("resume")
"""

from typing import Optional, List, Dict

import os
import glob
import platform
from pathlib import Path
from utils.logger import get_logger
import config

log = get_logger("pdf_reader")
PLATFORM = platform.system()


class PDFReader:
    """PDF text extraction and search."""

    # Common locations to search for PDFs
    SEARCH_DIRS = {
        "Darwin": [
            os.path.expanduser("~/Desktop"),
            os.path.expanduser("~/Downloads"),
            os.path.expanduser("~/Documents"),
        ],
        "Windows": [
            os.path.join(os.path.expanduser("~"), "Desktop"),
            os.path.join(os.path.expanduser("~"), "Downloads"),
            os.path.join(os.path.expanduser("~"), "Documents"),
        ],
        "Linux": [
            os.path.expanduser("~/Desktop"),
            os.path.expanduser("~/Downloads"),
            os.path.expanduser("~/Documents"),
        ],
    }

    def __init__(self):
        self._check_pymupdf()

    def _check_pymupdf(self):
        try:
            import fitz
            log.info("PyMuPDF available")
        except ImportError:
            log.error("PyMuPDF not installed. Run: pip install pymupdf")

    # ─── Text Extraction ─────────────────────────────────────────────────────

    def extract_text(self, path: str, max_pages: int = 20) -> str:
        """
        Extract text from a PDF file.
        Returns plain text string.
        """
        try:
            import fitz  # PyMuPDF

            doc = fitz.open(path)
            pages_to_read = min(len(doc), max_pages)
            text_parts = []

            for page_num in range(pages_to_read):
                page = doc[page_num]
                text = page.get_text("text")
                if text.strip():
                    text_parts.append(f"[Page {page_num + 1}]\n{text}")

            doc.close()
            full_text = "\n\n".join(text_parts)
            log.info(f"Extracted {len(full_text)} chars from {path} ({pages_to_read} pages)")
            return full_text

        except ImportError:
            return self._extract_fallback(path)
        except Exception as e:
            log.error(f"PDF extraction error for {path}: {e}")
            return ""

    def _extract_fallback(self, path: str) -> str:
        """Fallback using pdfplumber if PyMuPDF not available."""
        try:
            import pdfplumber

            with pdfplumber.open(path) as pdf:
                text = "\n".join(
                    page.extract_text() or ""
                    for page in pdf.pages[:20]
                )
            return text
        except ImportError:
            log.error("Neither pymupdf nor pdfplumber available.")
            return ""

    def extract_pages(self, path: str, start: int = 0, end: int = 5) -> str:
        """Extract specific page range (0-indexed)."""
        try:
            import fitz

            doc = fitz.open(path)
            text_parts = []
            for i in range(min(start, len(doc)), min(end, len(doc))):
                text_parts.append(doc[i].get_text("text"))
            doc.close()
            return "\n".join(text_parts)
        except Exception as e:
            log.error(f"Error extracting pages {start}-{end}: {e}")
            return ""

    # ─── File Finding ─────────────────────────────────────────────────────────

    def find_recent_pdf(self, hint: str = "") -> Optional[str]:
        """
        Find the most recently modified PDF matching a hint.
        If no hint, return the most recent PDF in common locations.
        """
        search_dirs = self.SEARCH_DIRS.get(PLATFORM, [os.path.expanduser("~")])

        candidates = []
        for directory in search_dirs:
            if not os.path.exists(directory):
                continue
            pdfs = glob.glob(os.path.join(directory, "**", "*.pdf"), recursive=True)
            candidates.extend(pdfs)

        if not candidates:
            log.warning("No PDF files found in common locations")
            return None

        # Filter by hint if provided
        if hint:
            hint_lower = hint.lower()
            matched = [p for p in candidates if hint_lower in os.path.basename(p).lower()]
            if matched:
                candidates = matched

        # Return most recently modified
        candidates.sort(key=lambda p: os.path.getmtime(p), reverse=True)
        result = candidates[0]
        log.info(f"Found PDF: {result}")
        return result

    def find_pdf_by_path(self, path_hint: str) -> Optional[str]:
        """Resolve a path hint to an actual file."""
        # Try direct path first
        if os.path.exists(path_hint) and path_hint.lower().endswith(".pdf"):
            return path_hint

        # Try expanding ~
        expanded = os.path.expanduser(path_hint)
        if os.path.exists(expanded):
            return expanded

        # Search by filename
        filename = os.path.basename(path_hint)
        return self.find_recent_pdf(filename.replace(".pdf", ""))

    # ─── Metadata ────────────────────────────────────────────────────────────

    def get_metadata(self, path: str) -> dict:
        """Return PDF metadata (title, author, pages, etc.)"""
        try:
            import fitz

            doc = fitz.open(path)
            meta = doc.metadata
            page_count = len(doc)
            doc.close()
            return {
                "title": meta.get("title", "Unknown"),
                "author": meta.get("author", "Unknown"),
                "pages": page_count,
                "subject": meta.get("subject", ""),
            }
        except Exception as e:
            log.error(f"Metadata error: {e}")
            return {}

    # ─── Smart Chunking for Long PDFs ────────────────────────────────────────

    def get_smart_chunks(self, path: str, chunk_size: int = None) -> list[str]:
        """
        Split PDF text into LLM-friendly chunks.
        Useful for long documents that exceed context window.
        """
        cs = chunk_size or config.PDF_CHUNK_SIZE
        full_text = self.extract_text(path)

        if not full_text:
            return []

        # Split by paragraphs, respecting chunk size
        paragraphs = full_text.split("\n\n")
        chunks = []
        current = []
        current_len = 0

        for para in paragraphs:
            para_len = len(para)
            if current_len + para_len > cs and current:
                chunks.append("\n\n".join(current))
                current = [para]
                current_len = para_len
            else:
                current.append(para)
                current_len += para_len

        if current:
            chunks.append("\n\n".join(current))

        log.info(f"Split PDF into {len(chunks)} chunks")
        return chunks
