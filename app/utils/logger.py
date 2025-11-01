"""
Structured logging utilities with GDPR compliance.
"""

import logging
import hashlib
import json
from datetime import datetime
from typing import Any, Dict


def hash_email(email: str) -> str:
    """
    Hash email for GDPR-safe logging.

    Args:
        email: Email address

    Returns:
        First 12 characters of SHA256 hash
    """
    return hashlib.sha256(email.encode()).hexdigest()[:12]


class JSONFormatter(logging.Formatter):
    """JSON log formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON.

        Args:
            record: Log record to format

        Returns:
            JSON-formatted log string
        """
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage()
        }

        # Add extra fields if provided
        if hasattr(record, 'extra_data'):
            log_data.update(record.extra_data)

        return json.dumps(log_data)


def get_logger(name: str) -> logging.Logger:
    """
    Get configured logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger with JSON formatting
    """
    logger = logging.getLogger(name)

    if not logger.handlers:
        from app.config import Config

        logger.setLevel(getattr(logging, Config.LOG_LEVEL))

        # Console handler
        console = logging.StreamHandler()
        console.setFormatter(JSONFormatter())
        logger.addHandler(console)

        # File handler
        if Config.LOG_FILE:
            file_handler = logging.FileHandler(Config.LOG_FILE)
            file_handler.setFormatter(JSONFormatter())
            logger.addHandler(file_handler)

    return logger


def log_with_context(
    logger: logging.Logger,
    level: str,
    message: str,
    **context
) -> None:
    """
    Log message with structured context.

    Args:
        logger: Logger instance
        level: Log level (INFO, WARNING, ERROR)
        message: Log message
        **context: Additional context fields
    """
    log_method = getattr(logger, level.lower())
    extra = {"extra_data": context}
    log_method(message, extra=extra)
