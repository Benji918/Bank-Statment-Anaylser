"""Celery tasks for file processing operations"""

from celery import current_task
from app.tasks.celery_app import celery_app
from app.services.file_service import file_service
from app.core.logging import get_logger

logger = get_logger(__name__)


@celery_app.task(name="cleanup_orphaned_files")
def cleanup_orphaned_files():
    """Clean up orphaned files from cloud storage"""
    
    try:
        from sqlalchemy.orm import Session
        from app.core.database import SessionLocal
        from app.models.statement import Statement, StatementStatus
        from datetime import datetime, timedelta
        
        db: Session = SessionLocal()
        
        # Find statements marked for deletion or failed more than 24 hours ago
        cleanup_threshold = datetime.utcnow() - timedelta(hours=24)
        
        statements_to_cleanup = db.query(Statement).filter(
            Statement.status.in_([StatementStatus.DELETED, StatementStatus.FAILED]),
            Statement.updated_at < cleanup_threshold,
            Statement.cloudinary_public_id.isnot(None)
        ).all()
        
        cleanup_count = 0
        for statement in statements_to_cleanup:
            try:
                # Delete from Cloudinary
                if file_service.delete_from_cloudinary(statement.cloudinary_public_id):
                    # Clear Cloudinary references
                    statement.cloudinary_public_id = None
                    statement.cloudinary_url = None
                    db.add(statement)
                    cleanup_count += 1
                    
            except Exception as e:
                logger.error(
                    f"Failed to cleanup file for statement {statement.id}: {str(e)}"
                )
        
        db.commit()
        db.close()
        
        logger.info(f"Cleaned up {cleanup_count} orphaned files")
        
        return {
            "status": "completed",
            "files_cleaned": cleanup_count
        }
        
    except Exception as e:
        logger.error(f"File cleanup task failed: {str(e)}")
        raise


@celery_app.task(name="validate_file_integrity")
def validate_file_integrity():
    """Validate integrity of stored files"""
    
    try:
        from sqlalchemy.orm import Session
        from app.core.database import SessionLocal
        from app.models.statement import Statement, StatementStatus
        import httpx
        
        db: Session = SessionLocal()
        
        # Get active statements with Cloudinary URLs
        statements = db.query(Statement).filter(
            Statement.status.in_([StatementStatus.UPLOADED, StatementStatus.COMPLETED]),
            Statement.cloudinary_url.isnot(None)
        ).limit(100).all()  # Process in batches
        
        validation_results = {
            "total_checked": 0,
            "valid_files": 0,
            "invalid_files": 0,
            "errors": []
        }
        
        for statement in statements:
            try:
                # Check if file exists and is accessible
                response = httpx.head(statement.cloudinary_url, timeout=10)
                
                if response.status_code == 200:
                    validation_results["valid_files"] += 1
                else:
                    validation_results["invalid_files"] += 1
                    validation_results["errors"].append({
                        "statement_id": statement.id,
                        "error": f"HTTP {response.status_code}"
                    })
                
                validation_results["total_checked"] += 1
                
                # Update task progress
                current_task.update_state(
                    state="PROGRESS",
                    meta={
                        "current": validation_results["total_checked"],
                        "total": len(statements),
                        "valid": validation_results["valid_files"],
                        "invalid": validation_results["invalid_files"]
                    }
                )
                
            except Exception as e:
                validation_results["invalid_files"] += 1
                validation_results["total_checked"] += 1
                validation_results["errors"].append({
                    "statement_id": statement.id,
                    "error": str(e)
                })
        
        db.close()
        
        logger.info(
            f"File integrity validation completed: "
            f"{validation_results['valid_files']} valid, "
            f"{validation_results['invalid_files']} invalid"
        )
        
        return validation_results
        
    except Exception as e:
        logger.error(f"File integrity validation failed: {str(e)}")
        raise