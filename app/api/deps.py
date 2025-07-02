"""API dependencies for authentication and database access"""

from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import security_service
from app.core.exceptions import unauthorized_exception
from app.models.user import User
from app.services.user_service import user_service

# Security scheme
security = HTTPBearer()


def get_current_user(
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """Get current authenticated user"""
    
    # Verify token
    user_id = security_service.verify_token(credentials.credentials)
    if not user_id:
        raise unauthorized_exception("Invalid or expired token")
    
    # Get user from database
    user = user_service.get(db, int(user_id))
    if not user or not user.is_active:
        raise unauthorized_exception("User not found or inactive")
    
    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current active user"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user


def get_current_premium_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """Get current premium user"""
    if not current_user.is_premium:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Premium subscription required"
        )
    return current_user


def get_current_admin_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """Get current admin user"""
    from app.models.user import UserRole
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user