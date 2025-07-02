"""User management endpoints"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import get_current_active_user
from app.schemas.user import UserResponse, UserUpdate, PasswordChange
from app.services.user_service import user_service
from app.models.user import User
from app.core.exceptions import ValidationError
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("/me", response_model=UserResponse)
def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """Get current user information"""
    return current_user


@router.put("/me", response_model=UserResponse)
def update_current_user(
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update current user information"""
    try:
        updated_user = user_service.update(db, current_user, user_update)
        logger.info("User updated successfully", user_id=current_user.id)
        return updated_user
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error("User update failed", error=str(e), user_id=current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Update failed"
        )


@router.post("/change-password")
def change_password(
    password_change: PasswordChange,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Change user password"""
    try:
        success = user_service.change_password(
            db,
            current_user,
            password_change.current_password,
            password_change.new_password
        )
        
        if success:
            logger.info("Password changed successfully", user_id=current_user.id)
            return {"message": "Password changed successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password change failed"
            )
            
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error("Password change failed", error=str(e), user_id=current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password change failed"
        )


@router.delete("/me")
def delete_current_user(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Soft delete current user account"""
    try:
        success = user_service.delete(db, current_user.id)
        
        if success:
            logger.info("User account deleted", user_id=current_user.id)
            return {"message": "Account deleted successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Account deletion failed"
            )
            
    except Exception as e:
        logger.error("Account deletion failed", error=str(e), user_id=current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Account deletion failed"
        )


@router.get("/subscription")
def get_subscription_info(
    current_user: User = Depends(get_current_active_user)
):
    """Get user subscription information"""
    return {
        "subscription_tier": current_user.subscription_tier.value,
        "is_premium": current_user.is_premium,
        "role": current_user.role.value
    }


@router.post("/subscription/upgrade")
def upgrade_subscription(
    new_tier: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Upgrade user subscription (mock implementation)"""
    try:
        # In a real implementation, this would:
        # 1. Validate payment information
        # 2. Process payment
        # 3. Update subscription
        
        updated_user = user_service.update_subscription(db, current_user, new_tier)
        
        logger.info(
            "Subscription upgraded",
            user_id=current_user.id,
            old_tier=current_user.subscription_tier.value,
            new_tier=new_tier
        )
        
        return {
            "message": "Subscription upgraded successfully",
            "new_tier": updated_user.subscription_tier.value
        }
        
    except Exception as e:
        logger.error("Subscription upgrade failed", error=str(e), user_id=current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Subscription upgrade failed"
        )