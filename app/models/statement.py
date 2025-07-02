"""Bank statement model"""

from sqlalchemy import Column, String, Integer, ForeignKey, Text, Float, Enum
from sqlalchemy.orm import relationship
from enum import Enum as PyEnum
from app.models.base import BaseModel


class StatementStatus(PyEnum):
    """Statement processing status"""
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DELETED = "deleted"


class StatementCategory(PyEnum):
    """Statement category"""
    PERSONAL = "personal"
    BUSINESS = "business"
    INVESTMENT = "investment"
    CREDIT_CARD = "credit_card"


class Statement(BaseModel):
    """Bank statement model"""
    
    __tablename__ = "statements"
    
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=False)
    file_type = Column(String(50), nullable=False)
    cloudinary_public_id = Column(String(255), nullable=True)
    cloudinary_url = Column(Text, nullable=True)
    
    # Processing status
    status = Column(Enum(StatementStatus), default=StatementStatus.UPLOADED, nullable=False)
    processing_started_at = Column(String(50), nullable=True)
    processing_completed_at = Column(String(50), nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Categorization
    category = Column(Enum(StatementCategory), default=StatementCategory.PERSONAL, nullable=False)
    bank_name = Column(String(100), nullable=True)
    account_type = Column(String(50), nullable=True)
    account_number_masked = Column(String(20), nullable=True)
    
    # Statement period
    statement_period_start = Column(String(50), nullable=True)
    statement_period_end = Column(String(50), nullable=True)
    
    # Metadata
    tags = Column(Text, nullable=True)  # JSON array as string
    notes = Column(Text, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="statements")
    analyses = relationship("Analysis", back_populates="statement", cascade="all, delete-orphan")
    
    @property
    def file_size_mb(self) -> float:
        """Get file size in MB"""
        return round(self.file_size / (1024 * 1024), 2)
    
    @property
    def is_processed(self) -> bool:
        """Check if statement is processed"""
        return self.status == StatementStatus.COMPLETED