"""Bank statement management endpoints"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import get_current_active_user
from app.schemas.statement import (
    StatementResponse, StatementCreate, StatementUpdate, 
    StatementUploadResponse, StatementListParams
)
from app.schemas.base import PaginatedResponse
from app.services.statement_service import statement_service
from app.models.user import User
from app.models.statement import StatementCategory
from app.core.exceptions import ValidationError, FileProcessingError
from app.core.logging import get_logger
import os
import tempfile
from app.services.pdf_service import PDFExcelService
import io, re, fitz

router = APIRouter()
logger = get_logger(__name__)


@router.post("/upload", response_model=List[StatementUploadResponse])
async def upload_statement(
    files: List[UploadFile] = File(...),
    category: StatementCategory = Form(StatementCategory.PERSONAL),
    bank_name: str = Form(None),
    account_type: str = Form(None),
    notes: str = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Upload a new bank statement"""
    responses = []

    for file in files:
        try:
            statement_data = StatementCreate(
                category=category,
                bank_name=bank_name,
                account_type=account_type,
                notes=notes
            )

            statement = await statement_service.upload_statement(
                db, file, current_user.id, statement_data
            )

            logger.info(
                "Statement uploaded successfully",
                statement_id=statement.id,
                user_id=current_user.id,
                filename=file.filename
            )

            responses.append(StatementUploadResponse(
                statement_id=statement.id,
                filename=statement.original_filename,
                file_size=statement.file_size,
                status=statement.status,
                message="Statement uploaded successfully"
            ))

        except (ValidationError, FileProcessingError) as e:
            responses.append(StatementUploadResponse(
                statement_id=None,
                filename=file.filename,
                file_size=0,
                status="FAILED",
                message=str(e)
            ))
            logger.error(
                "Statement upload failed",
                error=str(e),
                user_id=current_user.id,
                filename=file.filename
            )

        except Exception as e:
            responses.append(StatementUploadResponse(
                statement_id=None,
                filename=file.filename,
                file_size=0,
                status="FAILED",
                message="Statement upload failed"
            ))
            logger.error(
                "Statement upload failed",
                error=str(e),
                user_id=current_user.id,
                filename=file.filename
            )

    if not responses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files were uploaded"
        )

    return responses


@router.get("/", response_model=PaginatedResponse)
def get_statements(
    params: StatementListParams = Depends(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get user's bank statements with filtering and pagination"""
    try:
        statements, total = statement_service.get_user_statements(
            db, current_user.id, params
        )
        
        return PaginatedResponse.create(
            items=[StatementResponse.model_validate(stmt) for stmt in statements],
            total=total,
            pagination=params
        )
        
    except Exception as e:
        logger.error("Failed to get statements", error=str(e), user_id=current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve statements"
        )


@router.get("/{statement_id}", response_model=StatementResponse)
def get_statement(
    statement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get specific statement by ID"""
    try:
        statement = statement_service.get(db, statement_id)
        
        if not statement or statement.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Statement not found"
            )
        
        return StatementResponse.model_validate(statement)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to get statement",
            error=str(e),
            statement_id=statement_id,
            user_id=current_user.id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve statement"
        )


@router.put("/{statement_id}", response_model=StatementResponse)
def update_statement(
    statement_id: int,
    statement_update: StatementUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update statement information"""
    try:
        statement = statement_service.get(db, statement_id)
        
        if not statement or statement.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Statement not found"
            )
        
        updated_statement = statement_service.update(db, statement, statement_update)
        
        logger.info(
            "Statement updated successfully",
            statement_id=statement_id,
            user_id=current_user.id
        )
        
        return StatementResponse.model_validate(updated_statement)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to update statement",
            error=str(e),
            statement_id=statement_id,
            user_id=current_user.id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update statement"
        )


@router.delete("/{statement_id}")
def delete_statement(
    statement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete statement and associated files"""
    try:
        success = statement_service.delete_statement(db, statement_id, current_user.id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Statement not found"
            )
        
        logger.info(
            "Statement deleted successfully",
            statement_id=statement_id,
            user_id=current_user.id
        )
        
        return {"message": "Statement deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to delete statement",
            error=str(e),
            statement_id=statement_id,
            user_id=current_user.id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete statement"
        )


@router.get("/stats/summary")
def get_statement_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get statement statistics for current user"""
    try:
        stats = statement_service.get_statement_stats(db, current_user.id)
        return stats
        
    except Exception as e:
        logger.error("Failed to get statement stats", error=str(e), user_id=current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve statistics"
        )


@router.post("/bulk-delete")
def bulk_delete_statements(
    statement_ids: List[int],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete multiple statements"""
    try:
        deleted_count = 0
        errors = []
        
        for statement_id in statement_ids:
            try:
                success = statement_service.delete_statement(db, statement_id, current_user.id)
                if success:
                    deleted_count += 1
                else:
                    errors.append(f"Statement {statement_id} not found")
            except Exception as e:
                errors.append(f"Statement {statement_id}: {str(e)}")
        
        logger.info(
            "Bulk delete completed",
            user_id=current_user.id,
            deleted_count=deleted_count,
            error_count=len(errors)
        )
        
        return {
            "message": f"Deleted {deleted_count} statements",
            "deleted_count": deleted_count,
            "errors": errors
        }
        
    except Exception as e:
        logger.error("Bulk delete failed", error=str(e), user_id=current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Bulk delete failed"
        )

@router.post("/test-pdf-hashing")
async def analyze_statement(file: UploadFile = File(...)):
    patterns = {
        "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        "phone": r'\b(?:\+234|0)([789]\d{9})\b',
        "account_number": r'\b\d{10,20}\b',
        "address": r'\d+\s+\w+(?:\s+\w+)*\s+(Street|St|Avenue|Ave|Close|Rd|Road|Lane|Ln|Crescent|Cres)\b',
         "name": r'\b(?:[A-Z][A-Za-z\'\.-]+(?:\s+[A-Z][A-Za-z\'\.-]+){1,3}'
            r'|[A-Z]{2,}(?:\s+[A-Z]{2,}){1,3})\b',
        "bvn": r'\b\d{11}\b',
        "ssn": r'\b\d{3}-\d{2}-\d{4}\b',
        "credit_card": r'\b(?:\d{4}[- ]?){3}\d{4}\b',
        "routing_number": r'\b\d{9}\b',
        "iban": r'\b[A-Za-z]{2}\d{2}[A-Za-z0-9]{11,30}\b',
        # "swift_code": r'\b[A-Z]{4}[A-Z]{2}[A-Za-z0-9]{2}([A-Za-z0-9]{3})?\b',
        # "currency": r'\b[\$€¥₹£]?\d{1,3}(,\d{3})*(\.\d{1,2})?\b',
        "tin": r'\b\d{2}-\d{7}\b',
        "pan": r'\b[A-Z]{5}\d{4}[A-Z]\b',
        "gstin": r'\b\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z][Z][A-Z0-9]\b',
        # "cheque_number": r'\b\d{6,9}\b',
        "reference_number": r'\b[A-Z]{3,4}-\d{6,10}\b',
        # "business_reg": r'\b[A-Z0-9]{7,15}\b',
        # "sort_code": r'\b\d{9}\b',
        "ip_address": r'\b\d{1,3}(?:\.\d{1,3}){3}\b',
        "ipv4": r'\b\d{1,3}(?:\.\d{1,3}){3}\b',
        "url": r'\bhttps?://[^\s]+\b',
        "merchant_id": r'\b(M|C)-[A-Za-z0-9]{6,12}\b',
        "nin": r'\b\d{11}\b',
    }
    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        text = PDFExcelService.extract_text_from_pdf(tmp_path)
        anonymized_text = PDFExcelService.anonymize_text(text, patterns)
        # Send anonymized_text to Gemini LLM here
        return {"anonymized_text": anonymized_text}
    finally:
        os.unlink(tmp_path)  # Clean up