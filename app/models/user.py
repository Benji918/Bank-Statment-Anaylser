"""User model"""

from sqlalchemy import Column, String, Enum, DateTime, Text
from sqlalchemy.orm import relationship
from enum import Enum as PyEnum
from app.models.base import BaseModel


class UserRole(PyEnum):
    """User role enumeration"""
    ADMIN = "admin"
    USER = "user"
    PREMIUM = "premium"


class SubscriptionTier(PyEnum):
    """Subscription tier enumeration"""
    FREE = "free"
    BASIC = "basic"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class User(BaseModel):
    """User model"""
    
    __tablename__ = "users"
    
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    company = Column(String(255), nullable=True)
    role = Column(Enum(UserRole), default=UserRole.USER, nullable=False)
    subscription_tier = Column(
        Enum(SubscriptionTier), 
        default=SubscriptionTier.FREE, 
        nullable=False
    )
    last_login = Column(DateTime, nullable=True)
    email_verified = Column(String(1), default='N', nullable=False)
    phone = Column(String(20), nullable=True)
    avatar_url = Column(Text, nullable=True)
    preferences = Column(Text, nullable=True)  # JSON string
    
    # Relationships
    statements = relationship("Statement", back_populates="user", cascade="all, delete-orphan")
    analyses = relationship("Analysis", back_populates="user", cascade="all, delete-orphan")
    
    @property
    def full_name(self) -> str:
        """Get user's full name"""
        return f"{self.first_name} {self.last_name}"
    
    @property
    def is_premium(self) -> bool:
        """Check if user has premium subscription"""
        return self.subscription_tier in [
            SubscriptionTier.PROFESSIONAL, 
            SubscriptionTier.ENTERPRISE
        ]