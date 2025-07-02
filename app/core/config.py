"""Application configuration management"""

import os
from functools import lru_cache
from typing import Optional, List
from pydantic import Field, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Application
    APP_NAME: str = "IntelliBank API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = Field(default=False, env="DEBUG")
    API_V1_STR: str = "/api/v1"
    
    # Server
    HOST: str = Field(default="0.0.0.0", env="HOST")
    PORT: int = Field(default=8000, env="PORT")
    
    # Database
    DATABASE_URL: str = Field(..., env="DATABASE_URL")
    DATABASE_POOL_SIZE: int = Field(default=20, env="DATABASE_POOL_SIZE")
    DATABASE_MAX_OVERFLOW: int = Field(default=30, env="DATABASE_MAX_OVERFLOW")
    
    # Redis
    REDIS_URL: str = Field(..., env="REDIS_URL")
    
    # Security
    SECRET_KEY: str = Field(..., env="SECRET_KEY")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, env="REFRESH_TOKEN_EXPIRE_DAYS")
    ALGORITHM: str = "HS256"
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"],
        env="BACKEND_CORS_ORIGINS"
    )
    
    # Adobe PDF Services
    ADOBE_CLIENT_ID: str = Field(..., env="ADOBE_CLIENT_ID")
    ADOBE_CLIENT_SECRET: str = Field(..., env="ADOBE_CLIENT_SECRET")
    
    # Cloudinary
    CLOUDINARY_CLOUD_NAME: str = Field(..., env="CLOUDINARY_CLOUD_NAME")
    CLOUDINARY_API_KEY: str = Field(..., env="CLOUDINARY_API_KEY")
    CLOUDINARY_API_SECRET: str = Field(..., env="CLOUDINARY_API_SECRET")
    
    # Google Gemini
    GEMINI_API_KEY: str = Field(..., env="GEMINI_API_KEY")
    GEMINI_MODEL: str = Field(default="gemini-pro", env="GEMINI_MODEL")
    
    # File Processing
    MAX_FILE_SIZE: int = Field(default=50 * 1024 * 1024, env="MAX_FILE_SIZE")  # 50MB
    ALLOWED_FILE_TYPES: str = Field(default="application/pdf", env="ALLOWED_FILE_TYPES")
    
    # Celery
    CELERY_BROKER_URL: str = Field(..., env="CELERY_BROKER_URL")
    CELERY_RESULT_BACKEND: str = Field(..., env="CELERY_RESULT_BACKEND")
    
    # Monitoring
    SENTRY_DSN: Optional[str] = Field(default=None, env="SENTRY_DSN")
    PROMETHEUS_METRICS: bool = Field(default=True, env="PROMETHEUS_METRICS")
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = Field(default=60, env="RATE_LIMIT_PER_MINUTE")
    
    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v):
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings"""
    return Settings()


settings = get_settings()