"""Base service class with common functionality"""

from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Optional, List, Dict, Any
from sqlalchemy.orm import Session
from app.core.logging import LoggerMixin
from app.core.exceptions import DatabaseError, ValidationError

ModelType = TypeVar("ModelType")
CreateSchemaType = TypeVar("CreateSchemaType")
UpdateSchemaType = TypeVar("UpdateSchemaType")


class BaseService(Generic[ModelType, CreateSchemaType, UpdateSchemaType], LoggerMixin, ABC):
    """Base service class with CRUD operations"""
    
    def __init__(self, model: ModelType):
        self.model = model
    
    def get(self, db: Session, id: int) -> Optional[ModelType]:
        """Get single record by ID"""
        try:
            return db.query(self.model).filter(self.model.id == id).first()
        except Exception as e:
            self.log_error(e, "get_by_id", id=id)
            raise DatabaseError(f"Failed to get {self.model.__name__} by ID")
    
    def get_multi(
        self, 
        db: Session, 
        skip: int = 0, 
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[ModelType]:
        """Get multiple records with pagination and filters"""
        try:
            query = db.query(self.model)
            
            if filters:
                for key, value in filters.items():
                    if hasattr(self.model, key) and value is not None:
                        query = query.filter(getattr(self.model, key) == value)
            
            return query.offset(skip).limit(limit).all()
        except Exception as e:
            self.log_error(e, "get_multi", skip=skip, limit=limit, filters=filters)
            raise DatabaseError(f"Failed to get {self.model.__name__} records")
    
    def create(self, db: Session, obj_in: CreateSchemaType, **kwargs) -> ModelType:
        """Create new record"""
        try:
            obj_data = obj_in.model_dump() if hasattr(obj_in, 'model_dump') else obj_in.dict()
            obj_data.update(kwargs)
            db_obj = self.model(**obj_data)
            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)
            self.log_operation("create", model=self.model.__name__, id=db_obj.id)
            return db_obj
        except Exception as e:
            db.rollback()
            self.log_error(e, "create", model=self.model.__name__)
            raise DatabaseError(f"Failed to create {self.model.__name__}")
    
    def update(
        self, 
        db: Session, 
        db_obj: ModelType, 
        obj_in: UpdateSchemaType
    ) -> ModelType:
        """Update existing record"""
        try:
            obj_data = obj_in.model_dump(exclude_unset=True) if hasattr(obj_in, 'model_dump') else obj_in.dict(exclude_unset=True)
            
            for field, value in obj_data.items():
                if hasattr(db_obj, field):
                    setattr(db_obj, field, value)
            
            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)
            self.log_operation("update", model=self.model.__name__, id=db_obj.id)
            return db_obj
        except Exception as e:
            db.rollback()
            self.log_error(e, "update", model=self.model.__name__, id=db_obj.id)
            raise DatabaseError(f"Failed to update {self.model.__name__}")
    
    def delete(self, db: Session, id: int) -> bool:
        """Soft delete record"""
        try:
            obj = db.query(self.model).filter(self.model.id == id).first()
            if obj:
                obj.is_active = False
                db.add(obj)
                db.commit()
                self.log_operation("delete", model=self.model.__name__, id=id)
                return True
            return False
        except Exception as e:
            db.rollback()
            self.log_error(e, "delete", model=self.model.__name__, id=id)
            raise DatabaseError(f"Failed to delete {self.model.__name__}")
    
    def count(self, db: Session, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count records with optional filters"""
        try:
            query = db.query(self.model)
            
            if filters:
                for key, value in filters.items():
                    if hasattr(self.model, key) and value is not None:
                        query = query.filter(getattr(self.model, key) == value)
            
            return query.count()
        except Exception as e:
            self.log_error(e, "count", filters=filters)
            raise DatabaseError(f"Failed to count {self.model.__name__} records")