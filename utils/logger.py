"""
JARVIS Logger
=============
Configures a consistent logger for all modules.
"""

import logging
import os
import sys
from datetime import datetime
from config import LOGS_DIR, LOG_LEVEL, LOG_TO_FILE, DEBUG_MODE


def get_logger(name: str) -> logging.Logger:
    """Return a named logger with consistent formatting."""
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger  # Already configured

    level = logging.DEBUG if DEBUG_MODE else getattr(logging, LOG_LEVEL, logging.INFO)
    logger.setLevel(level)

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    # Console handler — always on
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(level)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    # File handler — optional
    if LOG_TO_FILE:
        log_file = os.path.join(
            LOGS_DIR, f"jarvis_{datetime.now().strftime('%Y%m%d')}.log"
        )
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setLevel(level)
        fh.setFormatter(fmt)
        logger.addHandler(fh)

    return logger
