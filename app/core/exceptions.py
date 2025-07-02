"""Custom exception classes"""

from typing import Any, Dict, Optional
from fastapi import HTTPException, status


class IntelliBaseException(Exception):
    """Base exception class for IntelliBank"""
    
    def __init__(
        self, 
        message: str, 
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(IntelliBaseException):
    """Validation error exception"""
    pass


class AuthenticationError(IntelliBaseException):
    """Authentication error exception"""
    pass


class AuthorizationError(IntelliBaseException):
    """Authorization error exception"""
    pass


class FileProcessingError(IntelliBaseException):
    """File processing error exception"""
    pass


class ExternalServiceError(IntelliBaseException):
    """External service error exception"""
    pass


class DatabaseError(IntelliBaseException):
    """Database operation error exception"""
    pass



# HTTP Exception factories
def create_http_exception(
    status_code: int,
    message: str,
    details: Optional[Dict[str, Any]] = None
) -> HTTPException:
    """Create HTTP exception with consistent format"""
    return HTTPException(
        status_code=status_code,
        detail={
            "message": message,
            "details": details or {}
        }
    )


def unauthorized_exception(message: str = "Authentication required") -> HTTPException:
    """Create unauthorized exception"""
    return create_http_exception(status.HTTP_401_UNAUTHORIZED, message)


def forbidden_exception(message: str = "Access forbidden") -> HTTPException:
    """Create forbidden exception"""
    return create_http_exception(status.HTTP_403_FORBIDDEN, message)


def not_found_exception(message: str = "Resource not found") -> HTTPException:
    """Create not found exception"""
    return create_http_exception(status.HTTP_404_NOT_FOUND, message)


def validation_exception(message: str, details: Dict[str, Any] = None) -> HTTPException:
    """Create validation exception"""
    return create_http_exception(status.HTTP_422_UNPROCESSABLE_ENTITY, message, details)


def server_error_exception(message: str = "Internal server error") -> HTTPException:
    """Create server error exception"""
    return create_http_exception(status.HTTP_500_INTERNAL_SERVER_ERROR, message)