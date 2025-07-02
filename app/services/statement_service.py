"""Statement service for managing bank statements"""

from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from fastapi import UploadFile
from app.models.statement import Statement, StatementStatus, StatementCategory
from app.schemas.statement import StatementCreate, StatementUpdate, StatementListParams
from app.services.base import BaseService
from app.services.file_service import file_service
from app.core.exceptions import ValidationError, FileProcessingError


class StatementService(BaseService[Statement, StatementCreate, StatementUpdate]):
    """Service for managing bank statements"""
    
    def __init__(self):
        super().__init__(Statement)
    
    async def upload_statement(
        self, 
        db: Session, 
        file: UploadFile, 
        user_id: int,
        statement_data: StatementCreate
    ) -> Statement:
        """Upload and create new statement record"""
        try:
            # Validate file
            file_service.validate_file(file)
            
            # Upload to Cloudinary
            public_id, secure_url = await file_service.upload_to_cloudinary(file, user_id)
            
            # Create statement record
            statement = self.create(
                db,
                statement_data,
                user_id=user_id,
                filename=file_service.generate_unique_filename(file.filename, user_id),
                original_filename=file.filename,
                file_size=file.size,
                file_type=file.content_type,
                cloudinary_public_id=public_id,
                cloudinary_url=secure_url,
                status=StatementStatus.UPLOADED
            )
            
            self.log_operation(
                "upload_statement",
                statement_id=statement.id,
                user_id=user_id,
                filename=file.filename
            )
            
            return statement
            
        except (ValidationError, FileProcessingError):
            raise
        except Exception as e:
            self.log_error(e, "upload_statement", user_id=user_id, filename=file.filename)
            raise FileProcessingError("Failed to upload statement")
    
    def get_user_statements(
        self, 
        db: Session, 
        user_id: int, 
        params: StatementListParams
    ) -> tuple[List[Statement], int]:
        """Get user statements with filtering and pagination"""
        try:
            query = db.query(Statement).filter(Statement.user_id == user_id)
            
            # Apply filters
            if params.category:
                query = query.filter(Statement.category == params.category)
            
            if params.status:
                query = query.filter(Statement.status == params.status)
            
            if params.bank_name:
                query = query.filter(Statement.bank_name.ilike(f"%{params.bank_name}%"))
            
            if params.search:
                search_filter = or_(
                    Statement.original_filename.ilike(f"%{params.search}%"),
                    Statement.bank_name.ilike(f"%{params.search}%"),
                    Statement.notes.ilike(f"%{params.search}%")
                )
                query = query.filter(search_filter)
            
            if params.start_date:
                query = query.filter(Statement.created_at >= params.start_date)
            
            if params.end_date:
                query = query.filter(Statement.created_at <= params.end_date)
            
            # Get total count
            total = query.count()
            
            # Apply pagination
            offset = (params.page - 1) * params.size
            statements = query.offset(offset).limit(params.size).all()
            
            self.log_operation(
                "get_user_statements",
                user_id=user_id,
                total=total,
                page=params.page
            )
            
            return statements, total
            
        except Exception as e:
            self.log_error(e, "get_user_statements", user_id=user_id)
            raise
    
    def update_processing_status(
        self, 
        db: Session, 
        statement_id: int, 
        status: StatementStatus,
        error_message: Optional[str] = None
    ) -> Statement:
        """Update statement processing status"""
        try:
            statement = self.get(db, statement_id)
            if not statement:
                raise ValidationError("Statement not found")
            
            statement.status = status
            if error_message:
                statement.error_message = error_message
            
            if status == StatementStatus.PROCESSING:
                from datetime import datetime
                statement.processing_started_at = datetime.utcnow()
            elif status in [StatementStatus.COMPLETED, StatementStatus.FAILED]:
                from datetime import datetime
                statement.processing_completed_at = datetime.utcnow()
            
            db.add(statement)
            db.commit()
            db.refresh(statement)
            
            self.log_operation(
                "update_processing_status",
                statement_id=statement_id,
                status=status.value
            )
            
            return statement
            
        except ValidationError:
            raise
        except Exception as e:
            self.log_error(e, "update_processing_status", statement_id=statement_id)
            raise
    
    def delete_statement(self, db: Session, statement_id: int, user_id: int) -> bool:
        """Delete statement and associated files"""
        try:
            statement = db.query(Statement).filter(
                and_(Statement.id == statement_id, Statement.user_id == user_id)
            ).first()
            
            if not statement:
                return False
            
            # Delete from Cloudinary
            if statement.cloudinary_public_id:
                file_service.delete_from_cloudinary(statement.cloudinary_public_id)
            
            # Soft delete the statement
            statement.is_active = False
            statement.status = StatementStatus.DELETED
            db.add(statement)
            db.commit()
            
            self.log_operation(
                "delete_statement",
                statement_id=statement_id,
                user_id=user_id
            )
            
            return True
            
        except Exception as e:
            self.log_error(e, "delete_statement", statement_id=statement_id)
            raise
    
    def get_statement_stats(self, db: Session, user_id: int) -> Dict[str, Any]:
        """Get statement statistics for user"""
        try:
            total_statements = db.query(Statement).filter(
                Statement.user_id == user_id
            ).count()
            
            completed_statements = db.query(Statement).filter(
                and_(
                    Statement.user_id == user_id,
                    Statement.status == StatementStatus.COMPLETED
                )
            ).count()
            
            processing_statements = db.query(Statement).filter(
                and_(
                    Statement.user_id == user_id,
                    Statement.status == StatementStatus.PROCESSING
                )
            ).count()
            
            failed_statements = db.query(Statement).filter(
                and_(
                    Statement.user_id == user_id,
                    Statement.status == StatementStatus.FAILED
                )
            ).count()
            
            # Get category distribution
            category_stats = db.query(
                Statement.category,
                db.func.count(Statement.id).label('count')
            ).filter(
                Statement.user_id == user_id
            ).group_by(Statement.category).all()
            
            stats = {
                "total_statements": total_statements,
                "completed_statements": completed_statements,
                "processing_statements": processing_statements,
                "failed_statements": failed_statements,
                "category_distribution": {
                    stat.category.value: stat.count for stat in category_stats
                }
            }
            
            self.log_operation("get_statement_stats", user_id=user_id, stats=stats)
            return stats
            
        except Exception as e:
            self.log_error(e, "get_statement_stats", user_id=user_id)
            return {}


# Create service instance
statement_service = StatementService()