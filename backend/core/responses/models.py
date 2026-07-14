"""
HELIOS OS + SEVRA AI
Standardized API Response Models

All API endpoints return one of these models.
Never return raw dicts from endpoints — always use these typed models.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field, computed_field

T = TypeVar("T")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


# ── Field-level Error (for validation failures) ───────────────────────────────

class FieldError(BaseModel):
    """Describes a single field-level validation error."""

    field: str = Field(description="The field path that failed validation")
    message: str = Field(description="Human-readable error message")
    error_type: str = Field(default="value_error", description="Pydantic error type code")


# ── Base Response ─────────────────────────────────────────────────────────────

class BaseResponse(BaseModel):
    """Base response wrapper included in every API response."""

    success: bool
    timestamp: datetime = Field(default_factory=_utc_now)
    request_id: str | None = Field(default=None)


# ── Success Response ──────────────────────────────────────────────────────────

class SuccessResponse(BaseResponse, Generic[T]):
    """
    Standard success response.
    
    Usage:
        return SuccessResponse(data=my_object, message="User created.")
    """

    success: bool = True
    message: str = Field(default="Operation completed successfully.")
    data: T | None = Field(default=None)


# ── Error Response ────────────────────────────────────────────────────────────

class ErrorResponse(BaseResponse):
    """
    Standard error response.
    
    Usage:
        return ErrorResponse(error_code="NOT_FOUND", message="User not found.")
    """

    success: bool = False
    error_code: str
    message: str
    field_errors: list[FieldError] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)


# ── Paginated Response ────────────────────────────────────────────────────────

class PaginationMeta(BaseModel):
    """Metadata for paginated responses."""

    page: int = Field(ge=1, description="Current page number (1-indexed)")
    page_size: int = Field(ge=1, le=1000, description="Items per page")
    total_items: int = Field(ge=0, description="Total number of items")

    @computed_field  # type: ignore[misc]
    @property
    def total_pages(self) -> int:
        if self.page_size == 0:
            return 0
        return max(1, (self.total_items + self.page_size - 1) // self.page_size)

    @computed_field  # type: ignore[misc]
    @property
    def has_next(self) -> bool:
        return self.page < self.total_pages

    @computed_field  # type: ignore[misc]
    @property
    def has_previous(self) -> bool:
        return self.page > 1


class PaginatedResponse(BaseResponse, Generic[T]):
    """
    Standard paginated list response.
    
    Usage:
        return PaginatedResponse(
            data=items,
            pagination=PaginationMeta(page=1, page_size=20, total_items=100)
        )
    """

    success: bool = True
    data: list[T] = Field(default_factory=list)
    pagination: PaginationMeta


# ── Health Response ───────────────────────────────────────────────────────────

class ServiceHealthStatus(BaseModel):
    """Health status of a single dependency."""

    name: str
    status: str  # "healthy" | "degraded" | "unhealthy"
    latency_ms: float | None = None
    message: str | None = None


class HealthResponse(BaseModel):
    """System health check response."""

    status: str  # "healthy" | "degraded" | "unhealthy"
    version: str
    environment: str
    timestamp: datetime = Field(default_factory=_utc_now)
    dependencies: list[ServiceHealthStatus] = Field(default_factory=list)

    @property
    def is_healthy(self) -> bool:
        return self.status == "healthy"
