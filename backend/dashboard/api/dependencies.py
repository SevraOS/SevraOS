"""
HELIOS OS + SEVRA AI
Dashboard FastAPI Dependencies (Security & DB)
"""

from typing import AsyncGenerator, List
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

from database.services.connection import db_manager
from database.services.uow import UnitOfWork
from dashboard.config import dash_config

security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Validate JWT token (Section 22 Security)."""
    try:
        payload = jwt.decode(
            credentials.credentials, 
            dash_config.JWT_SECRET_KEY, 
            algorithms=[dash_config.JWT_ALGORITHM]
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

def require_role(allowed_roles: List[str]):
    """RBAC Role Checker."""
    def role_checker(user: dict = Depends(get_current_user)):
        if user.get("role") not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
        return user
    return role_checker

async def get_uow() -> AsyncGenerator[UnitOfWork, None]:
    """Dependency injecting the Unit of Work for Postgres Reads."""
    # Assuming reads happen from Postgres in the Dashboard
    if not db_manager.pg_read_session_factory:
        raise RuntimeError("Database read connection not initialized")
        
    uow = UnitOfWork(db_manager.pg_read_session_factory)
    async with uow:
        yield uow

# Common Pagination Dependency
class PaginationParams:
    def __init__(self, skip: int = 0, limit: int = dash_config.DEFAULT_PAGE_SIZE):
        self.skip = skip
        self.limit = min(limit, dash_config.MAX_PAGE_SIZE)
