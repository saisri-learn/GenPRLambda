"""Structured logging for Lambda function."""

import json
import logging
import sys
import uuid
from datetime import datetime, timezone
from typing import Any


class StructuredLogger:
    """Logger that outputs structured JSON logs."""

    def __init__(self, name: str, level: str = "INFO") -> None:
        """Initialize the structured logger.

        Args:
            name: Logger name (typically __name__)
            level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.upper()))

        # Remove existing handlers
        self.logger.handlers.clear()

        # Create console handler with JSON formatter
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(self._json_formatter())
        self.logger.addHandler(handler)

        # Generate correlation ID for this execution
        self.correlation_id = str(uuid.uuid4())

    def _json_formatter(self) -> logging.Formatter:
        """Create a JSON formatter for log records."""

        class JsonFormatter(logging.Formatter):
            def format(self, record: logging.LogRecord) -> str:
                log_data = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "level": record.levelname,
                    "logger": record.name,
                    "message": record.getMessage(),
                }

                # Add correlation_id if available
                if hasattr(record, "correlation_id"):
                    log_data["correlation_id"] = record.correlation_id

                # Add stage if available
                if hasattr(record, "stage"):
                    log_data["stage"] = record.stage

                # Add metadata if available
                if hasattr(record, "metadata"):
                    log_data["metadata"] = record.metadata

                # Add exception info if present
                if record.exc_info:
                    log_data["exception"] = self.formatException(record.exc_info)

                return json.dumps(log_data)

        return JsonFormatter()

    def _log(
        self,
        level: int,
        message: str,
        stage: str | None = None,
        metadata: dict[str, Any] | None = None,
        exc_info: bool = False,
    ) -> None:
        """Internal method to log with structured data.

        Args:
            level: Logging level
            message: Log message
            stage: Optional stage identifier (e.g., "agent_execution", "mcp_connection")
            metadata: Optional metadata dictionary
            exc_info: Whether to include exception info
        """
        extra = {"correlation_id": self.correlation_id}
        if stage:
            extra["stage"] = stage
        if metadata:
            extra["metadata"] = metadata

        self.logger.log(level, message, extra=extra, exc_info=exc_info)

    def debug(
        self,
        message: str,
        stage: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Log a debug message."""
        self._log(logging.DEBUG, message, stage, metadata)

    def info(
        self,
        message: str,
        stage: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Log an info message."""
        self._log(logging.INFO, message, stage, metadata)

    def warning(
        self,
        message: str,
        stage: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Log a warning message."""
        self._log(logging.WARNING, message, stage, metadata)

    def error(
        self,
        message: str,
        stage: str | None = None,
        metadata: dict[str, Any] | None = None,
        exc_info: bool = False,
    ) -> None:
        """Log an error message."""
        self._log(logging.ERROR, message, stage, metadata, exc_info=exc_info)

    def critical(
        self,
        message: str,
        stage: str | None = None,
        metadata: dict[str, Any] | None = None,
        exc_info: bool = False,
    ) -> None:
        """Log a critical message."""
        self._log(logging.CRITICAL, message, stage, metadata, exc_info=exc_info)


# Global logger instance
_logger: StructuredLogger | None = None


def get_logger(name: str = __name__, level: str = "INFO") -> StructuredLogger:
    """Get or create the global logger instance.

    Args:
        name: Logger name
        level: Logging level

    Returns:
        StructuredLogger instance
    """
    global _logger
    if _logger is None:
        _logger = StructuredLogger(name, level)
    return _logger
