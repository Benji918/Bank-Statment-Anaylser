"""Security utilities for authentication and authorization"""

from datetime import datetime, timedelta
from typing import Optional, Union, Any
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import HTTPException, status
from pydantic import ValidationError

from app.core.config import settings

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class SecurityService:
    """Service for handling authentication and security operations"""
    
    @staticmethod
    def create_password_hash(password: str) -> str:
        """Create password hash"""
        return pwd_context.hash(password)
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def create_access_token(
        subject: Union[str, Any], 
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create JWT access token"""
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
            )
        
        to_encode = {"exp": expire, "sub": str(subject), "type": "access"}
        encoded_jwt = jwt.encode(
            to_encode, 
            settings.SECRET_KEY, 
            algorithm=settings.ALGORITHM
        )
        return encoded_jwt
    
    @staticmethod
    def create_refresh_token(subject: Union[str, Any]) -> str:
        """Create JWT refresh token"""
        expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode = {"exp": expire, "sub": str(subject), "type": "refresh"}
        encoded_jwt = jwt.encode(
            to_encode, 
            settings.SECRET_KEY, 
            algorithm=settings.ALGORITHM
        )
        return encoded_jwt
    
    @staticmethod
    def verify_token(token: str, token_type: str = "access") -> Optional[str]:
        """Verify JWT token and return subject"""
        try:
            payload = jwt.decode(
                token, 
                settings.SECRET_KEY, 
                algorithms=[settings.ALGORITHM]
            )
            
            if payload.get("type") != token_type:
                return None
                
            subject: str = payload.get("sub")
            if subject is None:
                return None
                
            return subject
            
        except (JWTError, ValidationError):
            return None


# Create security service instance
security_service = SecurityService()