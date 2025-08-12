"""Statement schemas"""

from typing import Optional, List
from datetime import datetime
from pydantic import Field, validator
from app.schemas.base import BaseSchema, TimestampMixin
from app.models.statement import StatementStatus, StatementCategory


class StatementBase(BaseSchema):
    """Base statement schema"""
    category: StatementCategory = StatementCategory.PERSONAL
    bank_name: Optional[str] = Field(None, max_length=100, alias='bank_name')
    account_type: Optional[str] = Field(None, max_length=50, alias='account_type')
    notes: Optional[str] = None


class StatementCreate(StatementBase):
    """Statement creation schema"""
    pass


class StatementUpdate(BaseSchema):
    """Statement update schema"""
    category: Optional[StatementCategory] = None
    bank_name: Optional[str] = Field(None, max_length=100, alias='bank_name')
    account_type: Optional[str] = Field(None, max_length=50, alias='account_type')
    notes: Optional[str] = None
    tags: Optional[List[str]] = None


class StatementResponse(StatementBase, TimestampMixin):
    """Statement response schema"""
    id: int
    user_id: int
    filename: str
    original_filename: str
    file_size: int
    file_type: str
    status: StatementStatus
    processing_started_at: Optional[datetime] = None
    processing_completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    account_number_masked: Optional[str] = None
    statement_period_start: Optional[str] = None
    statement_period_end: Optional[str] = None
    tags: Optional[List[str]] = None
    cloudinary_url: Optional[str] = None
    
    @property
    def file_size_mb(self) -> float:
        return round(self.file_size / (1024 * 1024), 2)


class StatementUploadResponse(BaseSchema):
    """Statement upload response schema"""
    statement_id: int
    filename: str
    file_size: int
    status: StatementStatus
    message: str


class StatementListParams(BaseSchema):
    """Statement list parameters"""
    category: Optional[StatementCategory] = None
    status: Optional[StatementStatus] = None
    bank_name: Optional[str] = None
    search: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)