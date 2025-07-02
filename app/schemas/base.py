"""Base schemas with common patterns"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    """Base schema with common configuration"""
    
    model_config = ConfigDict(
        from_attributes=True,
        validate_assignment=True,
        arbitrary_types_allowed=True
    )


class TimestampMixin(BaseSchema):
    """Mixin for timestamp fields"""
    created_at: datetime
    updated_at: datetime


class ResponseBase(BaseSchema):
    """Base response schema"""
    success: bool = True
    message: Optional[str] = None


class PaginationParams(BaseSchema):
    """Pagination parameters"""
    page: int = 1
    size: int = 20
    
    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size


class PaginatedResponse(ResponseBase):
    """Paginated response schema"""
    total: int
    page: int
    size: int
    pages: int
    
    @classmethod
    def create(cls, items, total: int, pagination: PaginationParams):
        """Create paginated response"""
        pages = (total + pagination.size - 1) // pagination.size
        return cls(
            data=items,
            total=total,
            page=pagination.page,
            size=pagination.size,
            pages=pages
        )