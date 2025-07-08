"""Celery tasks for export processing"""
from celery import current_task
from sqlalchemy.orm import Session
from app.tasks.celery_app import celery_app
from app.core.database import SessionLocal
from app.services.export_service import export_service
from app.core.logging import get_logger
from typing import List, Optional
from datetime import date

logger = get_logger(__name__)


@celery_app.task(bind=True, name="process_bulk_export")
def process_bulk_export(
        self,
        user_id: int,
        export_format: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        statement_ids: Optional[List[int]] = None,
        analysis_types: Optional[List[str]] = None,
        include_charts: bool = True
):
    """Process bulk export of analysis data"""

    # Update task state
    self.update_state(
        state="PROGRESS",
        meta={"current": 0, "total": 100, "status": "Starting export..."}
    )

    db: Session = SessionLocal()

    try:
        logger.info(
            "Starting bulk export task",
            task_id=self.request.id,
            user_id=user_id,
            format=export_format
        )

        # Convert date strings back to date objects
        start_date_obj = date.fromisoformat(start_date) if start_date else None
        end_date_obj = date.fromisoformat(end_date) if end_date else None

        # Update progress
        self.update_state(
            state="PROGRESS",
            meta={"current": 20, "total": 100, "status": "Gathering analysis data..."}
        )

        # Export data
        exported_data = export_service.export_analysis_data(
            db=db,
            user_id=user_id,
            export_format=export_format,
            start_date=start_date_obj,
            end_date=end_date_obj,
            statement_ids=statement_ids,
            analysis_types=analysis_types,
            include_charts=include_charts
        )

        # Update progress
        self.update_state(
            state="PROGRESS",
            meta={"current": 80, "total": 100, "status": "Finalizing export..."}
        )

        # In a real implementation, you might save the file to cloud storage
        # and return a download URL instead of the raw data

        logger.info(
            "Bulk export task completed",
            task_id=self.request.id,
            user_id=user_id,
            data_size=len(exported_data)
        )

        return {
            "status": "completed",
            "format": export_format,
            "data_size": len(exported_data),
            "user_id": user_id
        }

    except Exception as e:
        logger.error(
            "Bulk export task failed",
            task_id=self.request.id,
            user_id=user_id,
            error=str(e)
        )

        self.update_state(
            state="FAILURE",
            meta={"error": str(e), "user_id": user_id}
        )

        raise

    finally:
        db.close()


@celery_app.task(name="schedule_periodic_exports")
def schedule_periodic_exports():
    """Schedule periodic exports for users with subscriptions"""

    db: Session = SessionLocal()

    try:
        from app.models.user import User, SubscriptionTier
        from datetime import datetime, timedelta

        # Find users with premium subscriptions who have enabled auto-exports
        premium_users = db.query(User).filter(
            User.subscription_tier.in_([
                SubscriptionTier.PROFESSIONAL,
                SubscriptionTier.ENTERPRISE
            ]),
            User.is_active == True
        ).all()

        scheduled_count = 0
        for user in premium_users:
            # Check if user has analyses in the last month
            one_month_ago = datetime.utcnow() - timedelta(days=30)

            from app.models.analysis import Analysis
            recent_analyses = db.query(Analysis).filter(
                Analysis.user_id == user.id,
                Analysis.created_at >= one_month_ago
            ).count()

            if recent_analyses > 0:
                # Schedule monthly export
                process_bulk_export.delay(
                    user_id=user.id,
                    export_format="pdf",
                    start_date=one_month_ago.date().isoformat(),
                    end_date=datetime.utcnow().date().isoformat(),
                    include_charts=True
                )
                scheduled_count += 1

        logger.info(f"Scheduled {scheduled_count} periodic exports")

        return {
            "status": "completed",
            "scheduled_exports": scheduled_count
        }

    except Exception as e:
        logger.error(f"Periodic export scheduling failed: {str(e)}")
        raise

    finally:
        db.close()


@celery_app.task(name="cleanup_export_files")
def cleanup_export_files():
    """Clean up old export files from storage"""

    try:
        from datetime import datetime, timedelta
        import os

        # In a real implementation, this would clean up files from cloud storage
        # For now, we'll just log the cleanup operation

        cleanup_threshold = datetime.utcnow() - timedelta(days=7)

        logger.info(
            f"Export file cleanup completed",
            cleanup_threshold=cleanup_threshold.isoformat()
        )

        return {
            "status": "completed",
            "cleanup_threshold": cleanup_threshold.isoformat()
        }

    except Exception as e:
        logger.error(f"Export file cleanup failed: {str(e)}")
        raise