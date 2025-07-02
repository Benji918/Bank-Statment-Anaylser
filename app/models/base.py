"""Base model with common fields and methods"""

from datetime import datetime
from sqlalchemy import Column, Integer, DateTime, Boolean
from sqlalchemy.ext.declarative import declared_attr
from app.core.database import Base


class BaseModel(Base):
    """Base model with common fields"""
    
    __abstract__ = True
    
    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, 
        default=datetime.utcnow, 
        onupdate=datetime.utcnow, 
        nullable=False
    )
    is_active = Column(Boolean, default=True, nullable=False)
    
    @declared_attr
    def __tablename__(cls):
        """Generate table name from class name"""
        return cls.__name__.lower() + 's'
    
    def to_dict(self) -> dict:
        """Convert model to dictionary"""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }
    
    def update_from_dict(self, data: dict) -> None:
        """Update model from dictionary"""
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)