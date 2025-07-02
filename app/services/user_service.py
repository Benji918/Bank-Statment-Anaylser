"""User service for user management operations"""

from typing import Optional
from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.services.base import BaseService
from app.core.security import security_service
from app.core.exceptions import ValidationError, AuthenticationError


class UserService(BaseService[User, UserCreate, UserUpdate]):
    """User service with authentication logic"""
    
    def __init__(self):
        super().__init__(User)
    
    def get_by_email(self, db: Session, email: str) -> Optional[User]:
        """Get user by email"""
        try:
            return db.query(User).filter(User.email == email).first()
        except Exception as e:
            self.log_error(e, "get_by_email", email=email)
            raise
    
    def create_user(self, db: Session, user_in: UserCreate) -> User:
        """Create new user with password hashing"""
        try:
            # Check if user already exists
            existing_user = self.get_by_email(db, user_in.email)
            if existing_user:
                raise ValidationError("User with this email already exists")
            
            # Hash password
            hashed_password = security_service.create_password_hash(user_in.password)
            
            # Create user
            user_data = user_in.model_dump(exclude={'password', 'confirm_password'})
            user_data['hashed_password'] = hashed_password
            print(user_data.values())

            user = User(**user_data)
            db.add(user)
            db.commit()
            db.refresh(user)

            self.log_operation("create_user", user_id=user.id, email=user.email)
            return user
            
        except ValidationError:
            raise
        except Exception as e:
            self.log_error(e, "create_user", email=user_in.email)
            raise
    
    def authenticate(self, db: Session, email: str, password: str) -> Optional[User]:
        """Authenticate user with email and password"""
        try:
            user = self.get_by_email(db, email)
            if not user:
                return None
            
            if not security_service.verify_password(password, user.hashed_password):
                return None
            
            # self.log_operation("authenticate", user_id=user.id, email=email)
            return user
            
        except Exception as e:
            self.log_error(e, "authenticate", email=email)
            raise AuthenticationError("Authentication failed")
    
    def update_last_login(self, db: Session, user: User) -> User:
        """Update user's last login timestamp"""
        try:
            from datetime import datetime
            user.last_login = datetime.utcnow()
            db.add(user)
            db.commit()
            db.refresh(user)
            return user
        except Exception as e:
            self.log_error(e, "update_last_login", user_id=user.id)
            raise
    
    def change_password(
        self, 
        db: Session, 
        user: User, 
        current_password: str, 
        new_password: str
    ) -> bool:
        """Change user password"""
        try:
            # Verify current password
            if not security_service.verify_password(current_password, user.hashed_password):
                raise ValidationError("Current password is incorrect")
            
            # Hash new password
            hashed_password = security_service.create_password_hash(new_password)
            user.hashed_password = hashed_password
            
            db.add(user)
            db.commit()
            
            self.log_operation("change_password", user_id=user.id)
            return True
            
        except ValidationError:
            raise
        except Exception as e:
            self.log_error(e, "change_password", user_id=user.id)
            raise
    
    def update_subscription(
        self, 
        db: Session, 
        user: User, 
        subscription_tier: str
    ) -> User:
        """Update user subscription tier"""
        try:
            from app.models.user import SubscriptionTier
            user.subscription_tier = SubscriptionTier(subscription_tier)
            db.add(user)
            db.commit()
            db.refresh(user)
            
            self.log_operation(
                "update_subscription", 
                user_id=user.id, 
                new_tier=subscription_tier
            )
            return user
            
        except Exception as e:
            self.log_error(e, "update_subscription", user_id=user.id)
            raise


# Create service instance
user_service = UserService()