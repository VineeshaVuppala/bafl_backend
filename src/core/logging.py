"""
Logging configuration and utilities.
Provides structured logging with separate files for different log types.
"""
import logging
import sys
from pathlib import Path
from typing import Optional

from src.core.config import settings


# Create logs directory
LOGS_DIR = Path(__file__).parent.parent.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)


class LoggerConfig:
    """Logger configuration and setup."""
    
    _loggers: dict[str, logging.Logger] = {}
    
    @classmethod
    def setup_logger(
        cls,
        name: str,
        log_file: Optional[str] = None,
        level: Optional[int] = None
    ) -> logging.Logger:
        """
        Set up and return a configured logger.
        
        Args:
            name: Logger name
            log_file: Optional log file name (stored in logs/ directory)
            level: Optional logging level
            
        Returns:
            Configured logger instance
        """
        if name in cls._loggers:
            return cls._loggers[name]
        
        logger = logging.getLogger(name)
        logger.setLevel(level or getattr(logging, settings.LOG_LEVEL))
        logger.handlers = []  # Clear existing handlers
        
        # Create formatter
        formatter = logging.Formatter(
            settings.LOG_FORMAT,
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # File handler (if log_file specified)
        if log_file:
            file_handler = logging.FileHandler(
                LOGS_DIR / log_file,
                encoding="utf-8"
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        
        logger.propagate = False
        cls._loggers[name] = logger
        
        return logger


# Pre-configured loggers
api_logger = LoggerConfig.setup_logger("api", "api.log")
auth_logger = LoggerConfig.setup_logger("auth", "auth.log")
db_logger = LoggerConfig.setup_logger("database", "database.log")
error_logger = LoggerConfig.setup_logger("error", "error.log", logging.ERROR)


def log_api_request(method: str, path: str, status_code: int, username: str = "anonymous") -> None:
    """Log API request details."""
    api_logger.info(f"{method} {path} - {status_code} - User: {username}")


def log_auth_event(event: str, username: str, success: bool = True, details: str = "") -> None:
    """Log authentication events."""
    level = logging.INFO if success else logging.WARNING
    auth_logger.log(
        level,
        f"{event} - User: {username} - Success: {success}{f' - {details}' if details else ''}"
    )


def log_error(error: Exception, context: str = "") -> None:
    """Log errors with full traceback."""
    error_logger.error(
        f"Error{f' in {context}' if context else ''}: {str(error)}",
        exc_info=True
    )
