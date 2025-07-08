"""Export endpoints for analysis data"""

from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import get_current_active_user
from app.schemas.export import ExportRequest, ExportResponse
from app.services.export_service import export_service
from app.models.user import User
from app.core.exceptions import ValidationError, FileProcessingError
from app.core.logging import get_logger
import io

router = APIRouter()
logger = get_logger(__name__)


@router.post("/analysis", response_class=StreamingResponse)
def export_analysis_data(
        export_request: ExportRequest,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Export analysis data in specified format"""
    try:
        # Validate export format
        valid_formats = ['pdf', 'csv', 'excel', 'json', 'png']
        if export_request.format.lower() not in valid_formats:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid format. Supported formats: {', '.join(valid_formats)}"
            )


        exported_data = export_service.export_analysis_data(
            db=db,
            user_id=current_user.id,
            export_format=export_request.format,
            start_date=export_request.start_date,
            end_date=export_request.end_date,
            statement_ids=export_request.statement_ids,
            analysis_types=export_request.analysis_types,
            include_charts=export_request.include_charts
        )


        content_type, file_extension = _get_content_type_and_extension(export_request.format)
        filename = f"financial_analysis_{export_request.start_date or 'all'}_{export_request.end_date or 'data'}.{file_extension}"

        logger.info(
            "Analysis data exported successfully",
            user_id=current_user.id,
            format=export_request.format,
            filename=filename
        )

        return StreamingResponse(
            io.BytesIO(exported_data),
            media_type=content_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except (ValidationError, FileProcessingError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "Failed to export analysis data",
            error=str(e),
            user_id=current_user.id,
            format=export_request.format
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export analysis data"
        )


@router.get("/formats")
def get_supported_formats(
        current_user: User = Depends(get_current_active_user)
):
    """Get list of supported export formats"""
    return {
        "formats": [
            {
                "format": "pdf",
                "description": "Comprehensive PDF report with charts and analysis",
                "supports_charts": True,
                "file_extension": "pdf"
            },
            {
                "format": "excel",
                "description": "Excel workbook with multiple sheets for detailed data",
                "supports_charts": True,
                "file_extension": "xlsx"
            },
            {
                "format": "csv",
                "description": "Comma-separated values for data analysis",
                "supports_charts": False,
                "file_extension": "csv"
            },
            {
                "format": "json",
                "description": "Structured JSON data for API integration",
                "supports_charts": False,
                "file_extension": "json"
            },
            {
                "format": "png",
                "description": "High-resolution charts and visualizations",
                "supports_charts": True,
                "file_extension": "png"
            }
        ]
    }


@router.get("/preview/{analysis_id}")
def preview_export_data(
        analysis_id: int,
        format: str = Query(..., description="Export format"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Preview export data for a specific analysis"""
    try:
        # Validate format
        valid_formats = ['pdf', 'csv', 'excel', 'json', 'png']
        if format.lower() not in valid_formats:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid format. Supported formats: {', '.join(valid_formats)}"
            )

        # Get analysis
        from app.services.analysis_service import analysis_service
        analysis = analysis_service.get_analysis_with_statement(
            db, analysis_id, current_user.id
        )

        if not analysis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Analysis not found"
            )

        # Generate preview data (limited)
        if format.lower() == 'json':
            preview_data = {
                "analysis_id": analysis.id,
                "statement_filename": analysis.statement.original_filename if analysis.statement else None,
                "analysis_type": analysis.analysis_type,
                "financial_health_score": analysis.financial_health_score,
                "total_income": analysis.total_income,
                "total_expenses": analysis.total_expenses,
                "net_cash_flow": analysis.net_cash_flow,
                "summary_text": analysis.summary_text[:200] + "..." if analysis.summary_text and len(analysis.summary_text) > 200 else analysis.summary_text
            }
            return {"preview": preview_data, "format": format}
        else:
            return {
                "message": f"Preview available for {format} format",
                "analysis_id": analysis_id,
                "format": format,
                "estimated_size": _estimate_export_size([analysis], format)
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to preview export data",
            error=str(e),
            analysis_id=analysis_id,
            user_id=current_user.id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to preview export data"
        )


@router.get("/templates")
def get_export_templates(
        current_user: User = Depends(get_current_active_user)
):
    """Get predefined export templates"""
    return {
        "templates": [
            {
                "id": "executive_summary",
                "name": "Executive Summary",
                "description": "High-level overview with key metrics and insights",
                "recommended_format": "pdf",
                "includes": ["summary", "key_metrics", "charts"]
            },
            {
                "id": "detailed_analysis",
                "name": "Detailed Financial Analysis",
                "description": "Comprehensive analysis with all data points",
                "recommended_format": "excel",
                "includes": ["all_data", "insights", "recommendations", "charts"]
            },
            {
                "id": "data_export",
                "name": "Raw Data Export",
                "description": "All analysis data for further processing",
                "recommended_format": "csv",
                "includes": ["raw_data", "calculations"]
            },
            {
                "id": "visual_report",
                "name": "Visual Dashboard",
                "description": "Charts and visualizations only",
                "recommended_format": "png",
                "includes": ["charts", "graphs", "visualizations"]
            }
        ]
    }


def _get_content_type_and_extension(format: str) -> tuple[str, str]:
    """Get content type and file extension for format"""
    format_map = {
        'pdf': ('application/pdf', 'pdf'),
        'csv': ('text/csv', 'csv'),
        'excel': ('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'xlsx'),
        'json': ('application/json', 'json'),
        'png': ('image/png', 'png')
    }
    return format_map.get(format.lower(), ('application/octet-stream', 'bin'))


def _estimate_export_size(analyses: List, format: str) -> str:
    """Estimate export file size"""
    base_sizes = {
        'pdf': 50,  # KB per analysis
        'csv': 5,   # KB per analysis
        'excel': 25, # KB per analysis
        'json': 15,  # KB per analysis
        'png': 200   # KB per chart set
    }

    estimated_kb = base_sizes.get(format.lower(), 10) * len(analyses)

    if estimated_kb < 1024:
        return f"{estimated_kb} KB"
    else:
        return f"{estimated_kb / 1024:.1f} MB"