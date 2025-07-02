"""Financial analysis endpoints"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import get_current_active_user
from app.schemas.analysis import AnalysisResponse, AnalysisListParams, AnalysisStats
from app.schemas.base import PaginatedResponse
from app.services.analysis_service import analysis_service
from app.models.user import User
from app.core.exceptions import ValidationError, FileProcessingError
from app.core.logging import get_logger
from app.tasks.analysis_tasks import process_statement_analysis

router = APIRouter()
logger = get_logger(__name__)


@router.post("/{statement_id}/analyze")
def create_analysis(
    statement_id: int,
    analysis_type: str = "comprehensive",
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create financial analysis for a statement (async processing)"""
    try:
        # Validate statement exists and belongs to user
        from app.services.statement_service import statement_service
        statement = statement_service.get(db, statement_id)
        
        if not statement or statement.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Statement not found"
            )
        
        # Queue analysis task
        task = process_statement_analysis.delay(
            statement_id, current_user.id, analysis_type
        )
        
        logger.info(
            "Analysis task queued",
            task_id=task.id,
            statement_id=statement_id,
            user_id=current_user.id
        )
        
        return {
            "message": "Analysis started",
            "task_id": task.id,
            "statement_id": statement_id,
            "status": "queued"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to queue analysis",
            error=str(e),
            statement_id=statement_id,
            user_id=current_user.id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start analysis"
        )


@router.get("/task/{task_id}/status")
def get_analysis_task_status(task_id: str):
    """Get status of analysis task"""
    try:
        from app.tasks.celery_app import celery_app
        
        task_result = celery_app.AsyncResult(task_id)
        
        if task_result.state == "PENDING":
            response = {
                "task_id": task_id,
                "status": "pending",
                "message": "Task is waiting to be processed"
            }
        elif task_result.state == "PROGRESS":
            response = {
                "task_id": task_id,
                "status": "processing",
                "current": task_result.info.get("current", 0),
                "total": task_result.info.get("total", 100),
                "message": task_result.info.get("status", "Processing...")
            }
        elif task_result.state == "SUCCESS":
            response = {
                "task_id": task_id,
                "status": "completed",
                "result": task_result.result
            }
        else:  # FAILURE
            response = {
                "task_id": task_id,
                "status": "failed",
                "error": str(task_result.info)
            }
        
        return response
        
    except Exception as e:
        logger.error("Failed to get task status", error=str(e), task_id=task_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get task status"
        )


@router.get("/", response_model=PaginatedResponse)
def get_analyses(
    params: AnalysisListParams = Depends(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get user's financial analyses with filtering and pagination"""
    try:
        analyses, total = analysis_service.get_user_analyses(
            db, current_user.id, params
        )
        
        # Convert to response format
        analysis_responses = []
        for analysis in analyses:
            # Parse JSON fields back to objects
            import json
            
            response_data = {
                "id": analysis.id,
                "user_id": analysis.user_id,
                "statement_id": analysis.statement_id,
                "analysis_type": analysis.analysis_type,
                "model_version": analysis.model_version,
                "processing_time_seconds": analysis.processing_time_seconds,
                "total_income": analysis.total_income,
                "total_expenses": analysis.total_expenses,
                "net_cash_flow": analysis.net_cash_flow,
                "financial_health_score": analysis.financial_health_score,
                "summary_text": analysis.summary_text,
                "detailed_analysis": analysis.detailed_analysis,
                "created_at": analysis.created_at,
                "updated_at": analysis.updated_at
            }
            
            # Parse JSON fields
            try:
                if analysis.transaction_categories:
                    response_data["transaction_categories"] = json.loads(analysis.transaction_categories)
                if analysis.spending_patterns:
                    response_data["spending_patterns"] = json.loads(analysis.spending_patterns)
                if analysis.anomalies:
                    response_data["anomalies"] = json.loads(analysis.anomalies)
                if analysis.insights:
                    response_data["insights"] = json.loads(analysis.insights)
                if analysis.recommendations:
                    response_data["recommendations"] = json.loads(analysis.recommendations)
                if analysis.risk_assessment:
                    response_data["risk_assessment"] = json.loads(analysis.risk_assessment)
            except json.JSONDecodeError:
                pass  # Keep as None if JSON parsing fails
            
            analysis_responses.append(AnalysisResponse(**response_data))
        
        return PaginatedResponse.create(
            items=analysis_responses,
            total=total,
            pagination=params
        )
        
    except Exception as e:
        logger.error("Failed to get analyses", error=str(e), user_id=current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve analyses"
        )


@router.get("/{analysis_id}", response_model=AnalysisResponse)
def get_analysis(
    analysis_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get specific analysis by ID"""
    try:
        analysis = analysis_service.get_analysis_with_statement(
            db, analysis_id, current_user.id
        )
        
        if not analysis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Analysis not found"
            )
        
        # Convert to response format (similar to get_analyses)
        import json
        
        response_data = {
            "id": analysis.id,
            "user_id": analysis.user_id,
            "statement_id": analysis.statement_id,
            "analysis_type": analysis.analysis_type,
            "model_version": analysis.model_version,
            "processing_time_seconds": analysis.processing_time_seconds,
            "total_income": analysis.total_income,
            "total_expenses": analysis.total_expenses,
            "net_cash_flow": analysis.net_cash_flow,
            "financial_health_score": analysis.financial_health_score,
            "summary_text": analysis.summary_text,
            "detailed_analysis": analysis.detailed_analysis,
            "created_at": analysis.created_at,
            "updated_at": analysis.updated_at
        }
        
        # Parse JSON fields
        try:
            if analysis.transaction_categories:
                response_data["transaction_categories"] = json.loads(analysis.transaction_categories)
            if analysis.spending_patterns:
                response_data["spending_patterns"] = json.loads(analysis.spending_patterns)
            if analysis.anomalies:
                response_data["anomalies"] = json.loads(analysis.anomalies)
            if analysis.insights:
                response_data["insights"] = json.loads(analysis.insights)
            if analysis.recommendations:
                response_data["recommendations"] = json.loads(analysis.recommendations)
            if analysis.risk_assessment:
                response_data["risk_assessment"] = json.loads(analysis.risk_assessment)
        except json.JSONDecodeError:
            pass
        
        return AnalysisResponse(**response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to get analysis",
            error=str(e),
            analysis_id=analysis_id,
            user_id=current_user.id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve analysis"
        )


@router.delete("/{analysis_id}")
def delete_analysis(
    analysis_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete analysis"""
    try:
        analysis = analysis_service.get(db, analysis_id)
        
        if not analysis or analysis.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Analysis not found"
            )
        
        success = analysis_service.delete(db, analysis_id)
        
        if success:
            logger.info(
                "Analysis deleted successfully",
                analysis_id=analysis_id,
                user_id=current_user.id
            )
            return {"message": "Analysis deleted successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to delete analysis"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to delete analysis",
            error=str(e),
            analysis_id=analysis_id,
            user_id=current_user.id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete analysis"
        )


@router.get("/stats/summary", response_model=AnalysisStats)
def get_analysis_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get analysis statistics for current user"""
    try:
        stats = analysis_service.get_analysis_stats(db, current_user.id)
        return AnalysisStats(**stats)
        
    except Exception as e:
        logger.error("Failed to get analysis stats", error=str(e), user_id=current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve statistics"
        )


@router.post("/batch-analyze")
def batch_analyze_statements(
    statement_ids: List[int],
    analysis_type: str = "comprehensive",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Analyze multiple statements in batch"""
    try:
        from app.tasks.analysis_tasks import batch_process_statements
        
        # Validate all statements belong to user
        from app.services.statement_service import statement_service
        valid_statement_ids = []
        
        for statement_id in statement_ids:
            statement = statement_service.get(db, statement_id)
            if statement and statement.user_id == current_user.id:
                valid_statement_ids.append(statement_id)
        
        if not valid_statement_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid statements found"
            )
        
        # Queue batch processing task
        task = batch_process_statements.delay(valid_statement_ids, current_user.id)
        
        logger.info(
            "Batch analysis task queued",
            task_id=task.id,
            statement_count=len(valid_statement_ids),
            user_id=current_user.id
        )
        
        return {
            "message": "Batch analysis started",
            "task_id": task.id,
            "statement_count": len(valid_statement_ids),
            "status": "queued"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to queue batch analysis",
            error=str(e),
            user_id=current_user.id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start batch analysis"
        )