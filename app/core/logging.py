"""Structured logging configuration"""

import sys
import structlog
from typing import Any, Dict
from app.core.config import settings


def configure_logging() -> None:
    """Configure structured logging"""
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer() if not settings.DEBUG 
            else structlog.dev.ConsoleRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """Get structured logger instance"""
    return structlog.get_logger(name)


class LoggerMixin:
    """Mixin to add logging capabilities to classes"""
    
    @property
    def logger(self) -> structlog.BoundLogger:
        """Get logger for this class"""
        return get_logger(self.__class__.__name__)
    
    def log_operation(
        self, 
        operation: str, 
        **kwargs: Any
    ) -> None:
        """Log operation with context"""
        self.logger.info(
            f"Operation: {operation}",
            operation=operation,
            **kwargs
        )
    
    def log_error(
        self, 
        error: Exception, 
        operation: str = None,
        **kwargs: Any
    ) -> None:
        """Log error with context"""
        self.logger.error(
            f"Error in {operation or 'operation'}: {str(error)}",
            error=str(error),
            error_type=type(error).__name__,
            operation=operation,
            **kwargs
        )