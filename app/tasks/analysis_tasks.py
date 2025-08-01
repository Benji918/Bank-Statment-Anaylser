"""Celery tasks for financial analysis processing"""
import asyncio

from celery import current_task
from sqlalchemy.orm import Session
from app.tasks.celery_app import celery_app
from app.core.database import SessionLocal
from app.services.analysis_service import analysis_service
from app.core.logging import get_logger

logger = get_logger(__name__)


@celery_app.task(bind=True, name="process_statement_analysis")
def process_statement_analysis(
        self,
        statement_id: int,
        user_id: int,
        analysis_type: str = "comprehensive"
):
    """Process financial analysis for a bank statement"""


    self.update_state(
        state="PROGRESS",
        meta={"current": 0, "total": 100, "status": "Starting analysis..."}
    )

    db: Session = SessionLocal()

    try:
        logger.info(
            "Starting analysis task",
            task_id=self.request.id,
            statement_id=statement_id,
            user_id=user_id
        )

        self.update_state(
            state="PROGRESS",
            meta={"current": 20, "total": 100, "status": "Downloading file..."}
        )

        # Handle async function call properly
        try:
            # Get or create event loop for async function
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # Run the async function and get the actual result
            analysis = loop.run_until_complete(
                analysis_service.create_analysis(
                    db, statement_id, user_id, analysis_type
                )
            )

        except Exception as async_error:
            logger.error(f"Async analysis creation failed: {str(async_error)}")



        self.update_state(
            state="PROGRESS",
            meta={"current": 50, "total": 100, "status": "Processing with AI..."}
        )


        self.update_state(
            state="PROGRESS",
            meta={"current": 90, "total": 100, "status": "Finalizing results..."}
        )

        logger.info(
            "Analysis task completed",
            task_id=self.request.id,
            analysis_id=analysis.id,
            statement_id=statement_id
        )

        return {
            "status": "completed",
            "analysis_id": analysis.id,
            "statement_id": statement_id,
            "financial_health_score": analysis.financial_health_score,
            "processing_time": analysis.processing_time_seconds
        }

    except Exception as e:
        logger.error(
            "Analysis task failed",
            task_id=self.request.id,
            statement_id=statement_id,
            error=str(e)
        )

        # Update statement status to failed
        try:
            from app.services.statement_service import statement_service
            from app.models.statement import StatementStatus
            statement_service.update_processing_status(
                db, statement_id, StatementStatus.FAILED, str(e)
            )
        except:
            pass

        self.update_state(
            state="FAILURE",
            meta={"error": str(e), "statement_id": statement_id}
        )

        raise

    finally:
        db.close()


@celery_app.task(name="batch_process_statements")
def batch_process_statements(statement_ids: list, user_id: int):
    """Process multiple statements in batch"""
    
    results = []
    total = len(statement_ids)
    
    for i, statement_id in enumerate(statement_ids):
        try:

            result = process_statement_analysis.delay(statement_id, user_id)
            results.append({
                "statement_id": statement_id,
                "task_id": result.id,
                "status": "queued"
            })
            

            current_task.update_state(
                state="PROGRESS",
                meta={
                    "current": i + 1,
                    "total": total,
                    "status": f"Queued {i + 1}/{total} statements"
                }
            )
            
        except Exception as e:
            results.append({
                "statement_id": statement_id,
                "error": str(e),
                "status": "failed"
            })

    
    return {
        "status": "completed",
        "total_statements": total,
        "results": results
    }


@celery_app.task(name="cleanup_failed_analyses")
def cleanup_failed_analyses():
    """Cleanup failed analysis records and update statement statuses"""
    
    db: Session = SessionLocal()
    
    try:
        from app.models.statement import Statement, StatementStatus
        from datetime import datetime, timedelta
        
        # Find statements stuck in processing for more than 1 hour
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        
        stuck_statements = db.query(Statement).filter(
            Statement.status == StatementStatus.PROCESSING,
            Statement.processing_started_at < one_hour_ago
        ).all()
        
        cleanup_count = 0
        for statement in stuck_statements:
            statement.status = StatementStatus.FAILED
            statement.error_message = "Processing timeout - task may have failed"
            db.add(statement)
            cleanup_count += 1
        
        db.commit()
        
        logger.info(f"Cleaned up {cleanup_count} stuck statements")
        
        return {
            "status": "completed",
            "cleaned_up_count": cleanup_count
        }
        
    except Exception as e:
        logger.error(f"Cleanup task failed: {str(e)}")

        db.rollback()
        raise
        
    finally:
        db.close()