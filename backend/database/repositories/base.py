"""
HELIOS OS + SEVRA AI
Base Repository Pattern
"""

from typing import Generic, TypeVar, Type, Optional, List, Sequence, Any, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, asc, desc
from sqlalchemy.orm import DeclarativeBase

ModelType = TypeVar("ModelType", bound=DeclarativeBase)

class BaseRepository(Generic[ModelType]):
    """
    Base repository providing standard CRUD and pagination operations.
    """
    def __init__(self, model: Type[ModelType], session: AsyncSession):
        self.model = model
        self.session = session

    async def get_by_id(self, id: str) -> Optional[ModelType]:
        """Fetch a single record by UUID."""
        stmt = select(self.model).where(self.model.id == id).where(self.model.deleted_at.is_(None))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_client_event_id(self, client_event_id: str) -> Optional[ModelType]:
        """Fetch a single record by its idempotency key."""
        stmt = select(self.model).where(getattr(self.model, "client_event_id") == client_event_id).where(self.model.deleted_at.is_(None))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_multi(
        self, 
        *, 
        skip: int = 0, 
        limit: int = 100, 
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        order_desc: bool = False
    ) -> Sequence[ModelType]:
        """Fetch multiple records with optional pagination, filtering, and sorting."""
        stmt = select(self.model).where(self.model.deleted_at.is_(None))
        
        if filters:
            for key, value in filters.items():
                if hasattr(self.model, key):
                    stmt = stmt.where(getattr(self.model, key) == value)

        if order_by and hasattr(self.model, order_by):
            column = getattr(self.model, order_by)
            stmt = stmt.order_by(desc(column) if order_desc else asc(column))
        else:
            # Default order by created_at desc
            stmt = stmt.order_by(desc(self.model.created_at))

        stmt = stmt.offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def create(self, obj_in: Dict[str, Any]) -> ModelType:
        """Create a new record."""
        db_obj = self.model(**obj_in)
        self.session.add(db_obj)
        # We don't commit here. The Unit of Work handles that.
        return db_obj

    async def create_multi(self, objs_in: List[Dict[str, Any]]) -> List[ModelType]:
        """Bulk create records."""
        db_objs = [self.model(**obj) for obj in objs_in]
        self.session.add_all(db_objs)
        return db_objs

    async def update(self, id: str, obj_in: Dict[str, Any]) -> Optional[ModelType]:
        """Update an existing record."""
        db_obj = await self.get_by_id(id)
        if not db_obj:
            return None
            
        for field, value in obj_in.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
                
        self.session.add(db_obj)
        return db_obj

    async def soft_delete(self, id: str, actor: str = "system") -> bool:
        """Soft delete a record."""
        db_obj = await self.get_by_id(id)
        if not db_obj:
            return False
            
        db_obj.soft_delete(actor=actor)
        self.session.add(db_obj)
        return True

    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count records matching filters."""
        stmt = select(func.count()).select_from(self.model).where(self.model.deleted_at.is_(None))
        
        if filters:
            for key, value in filters.items():
                if hasattr(self.model, key):
                    stmt = stmt.where(getattr(self.model, key) == value)
                    
        result = await self.session.execute(stmt)
        return result.scalar_one()
