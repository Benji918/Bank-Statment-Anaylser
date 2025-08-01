"""Export schemas for request/response validation"""

from typing import Optional, List
from datetime import date
from pydantic import Field, validator
from app.schemas.base import BaseSchema


class ExportRequest(BaseSchema):
    """Export request schema"""
    format: str = Field(..., description="Export format (pdf, csv, excel, json, png)")
    start_date: Optional[date] = Field(None, description="Start date for filtering", alias="start_date")
    end_date: Optional[date] = Field(None, description="End date for filtering", alias='end_date' )
    statement_ids: Optional[List[int]] = Field(None, description="Specific statement IDs to export", alias="statement_ids")
    analysis_types: Optional[List[str]] = Field(None, description="Types of analysis to include", alias="analysis_types")
    include_charts: bool = Field(True, description="Whether to include charts in export", alias="include_charts")
    template: Optional[str] = Field(None, description="Predefined template to use", alias="template")

    @validator('format')
    def validate_format(cls, v):
        valid_formats = ['pdf', 'csv', 'excel', 'json', 'png']
        if v.lower() not in valid_formats:
            raise ValueError(f'Format must be one of: {", ".join(valid_formats)}')
        return v.lower()

    @validator('end_date')
    def validate_date_range(cls, v, values):
        if v and 'start_date' in values and values['start_date']:
            if v < values['start_date']:
                raise ValueError('End date must be after start date')
        return v


class ExportResponse(BaseSchema):
    """Export response schema"""
    success: bool = True
    message: str = "Export completed successfully"
    filename: str
    format: str
    file_size: Optional[int] = None
    download_url: Optional[str] = None


class ExportTemplate(BaseSchema):
    """Export template schema"""
    id: str
    name: str
    description: str
    recommended_format: str
    includes: List[str]


class ExportFormat(BaseSchema):
    """Export format schema"""
    format: str
    description: str
    supports_charts: bool
    file_extension: str


class ExportPreview(BaseSchema):
    """Export preview schema"""
    analysis_id: int
    format: str
    estimated_size: str
    preview_data: Optional[dict] = None