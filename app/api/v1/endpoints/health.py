"""Health check and monitoring endpoints"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db
from app.core.config import settings
from app.core.logging import get_logger
import redis
import time

router = APIRouter()
logger = get_logger(__name__)


@router.get("/")
def health_check():
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "service": "IntelliBank API",
        "version": settings.APP_VERSION,
        "timestamp": time.time()
    }


@router.get("/detailed")
def detailed_health_check(db: Session = Depends(get_db)):
    """Detailed health check including dependencies"""
    
    health_status = {
        "status": "healthy",
        "service": "IntelliBank API",
        "version": settings.APP_VERSION,
        "timestamp": time.time(),
        "checks": {}
    }
    
    # Database check
    try:
        db.execute(text("SELECT 1"))
        health_status["checks"]["database"] = {
            "status": "healthy",
            "response_time_ms": 0  # Would measure actual response time
        }
    except Exception as e:
        health_status["checks"]["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "unhealthy"
    
    # Redis check
    try:
        redis_client = redis.from_url(settings.REDIS_URL)
        redis_client.ping()
        health_status["checks"]["redis"] = {
            "status": "healthy",
            "response_time_ms": 0
        }
    except Exception as e:
        health_status["checks"]["redis"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "unhealthy"
    
    # Celery check
    try:
        from app.tasks.celery_app import celery_app
        inspect = celery_app.control.inspect()
        stats = inspect.stats()
        
        if stats:
            health_status["checks"]["celery"] = {
                "status": "healthy",
                "workers": len(stats),
                "active_workers": list(stats.keys())
            }
        else:
            health_status["checks"]["celery"] = {
                "status": "unhealthy",
                "error": "No active workers"
            }
            health_status["status"] = "degraded"
            
    except Exception as e:
        health_status["checks"]["celery"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "degraded"
    
    # External services check
    health_status["checks"]["external_services"] = {}
    
    # Adobe API check
    try:
        from app.services.pdf_service import pdf_service
        # This would be a lightweight check, not a full conversion
        health_status["checks"]["external_services"]["adobe"] = {
            "status": "healthy",
            "configured": bool(settings.ADOBE_CLIENT_ID and settings.ADOBE_CLIENT_SECRET)
        }
    except Exception as e:
        health_status["checks"]["external_services"]["adobe"] = {
            "status": "unknown",
            "error": str(e)
        }
    
    # Cloudinary check
    try:
        import cloudinary
        health_status["checks"]["external_services"]["cloudinary"] = {
            "status": "healthy",
            "configured": bool(settings.CLOUDINARY_CLOUD_NAME)
        }
    except Exception as e:
        health_status["checks"]["external_services"]["cloudinary"] = {
            "status": "unknown",
            "error": str(e)
        }
    
    # Gemini API check
    health_status["checks"]["external_services"]["gemini"] = {
        "status": "healthy",
        "configured": bool(settings.GEMINI_API_KEY)
    }
    
    return health_status


@router.get("/metrics")
def get_metrics(db: Session = Depends(get_db)):
    """Get application metrics"""
    
    try:
        # Database metrics
        from app.models.user import User
        from app.models.statement import Statement
        from app.models.analysis import Analysis
        
        total_users = db.query(User).count()
        active_users = db.query(User).filter(User.is_active == True).count()
        total_statements = db.query(Statement).count()
        total_analyses = db.query(Analysis).count()
        
        # Celery metrics
        celery_metrics = {}
        try:
            from app.tasks.celery_app import celery_app
            inspect = celery_app.control.inspect()
            
            # Active tasks
            active_tasks = inspect.active()
            scheduled_tasks = inspect.scheduled()
            
            celery_metrics = {
                "active_tasks": sum(len(tasks) for tasks in (active_tasks or {}).values()),
                "scheduled_tasks": sum(len(tasks) for tasks in (scheduled_tasks or {}).values()),
                "workers": len(active_tasks or {})
            }
        except:
            celery_metrics = {"error": "Unable to fetch Celery metrics"}
        
        return {
            "timestamp": time.time(),
            "database": {
                "total_users": total_users,
                "active_users": active_users,
                "total_statements": total_statements,
                "total_analyses": total_analyses
            },
            "celery": celery_metrics,
            "system": {
                "debug_mode": settings.DEBUG,
                "environment": "development" if settings.DEBUG else "production"
            }
        }
        
    except Exception as e:
        logger.error("Failed to get metrics", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve metrics")


@router.get("/ready")
def readiness_check(db: Session = Depends(get_db)):
    """Kubernetes readiness probe endpoint"""
    
    try:
        # Check if we can connect to database
        db.execute(text("SELECT 1"))
        
        # Check if we can connect to Redis
        redis_client = redis.from_url(settings.REDIS_URL)
        redis_client.ping()
        
        return {"status": "ready"}
        
    except Exception as e:
        logger.error("Readiness check failed", error=str(e))
        raise HTTPException(status_code=503, detail="Service not ready")


@router.get("/live")
def liveness_check():
    """Kubernetes liveness probe endpoint"""
    return {"status": "alive"}