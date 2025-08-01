"""User schemas"""

from typing import Optional
from pydantic import EmailStr, Field, validator
from app.schemas.base import BaseSchema, TimestampMixin
from app.models.user import UserRole, SubscriptionTier


class UserBase(BaseSchema):
    """Base user schema"""
    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=100, alias='first_name')
    last_name: str = Field(..., min_length=1, max_length=100, alias='last_name')
    company: Optional[str] = Field(None, max_length=255, alias='companyName')


class UserCreate(UserBase):
    """User creation schema"""
    password: str = Field(..., min_length=8, max_length=100, alias='password')
    confirm_password: str
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'password' in values and v != values['password']:
            raise ValueError('Passwords do not match')
        return v


class UserUpdate(BaseSchema):
    """User update schema"""
    first_name: Optional[str] = Field(None, min_length=1, max_length=100, alias='first_name')
    last_name: Optional[str] = Field(None, min_length=1, max_length=100, alias='last_name')
    company: Optional[str] = Field(None, max_length=255, alias='companyName')
    phone: Optional[str] = Field(None, max_length=20, alias='phoneNumber')


class UserResponse(UserBase, TimestampMixin):
    """User response schema"""
    id: int
    role: UserRole
    subscription_tier: SubscriptionTier
    email_verified: str
    phone: Optional[str] = None
    avatar_url: Optional[str] = None
    is_active: bool
    
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


class UserLogin(BaseSchema):
    """User login schema"""
    email: EmailStr
    password: str


class TokenResponse(BaseSchema):
    """Token response schema"""
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int


class PasswordChange(BaseSchema):
    """Password change schema"""
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=100, alias='newPassword')
    confirm_password: str
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v