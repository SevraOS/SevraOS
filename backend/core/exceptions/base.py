"""
HELIOS OS + SEVRA AI
Exception Hierarchy

Custom exception classes organized by layer:
  - Base exceptions
  - Infrastructure exceptions (DB, Redis, network)
  - Business/Domain exceptions
  - HTTP/API exceptions
  - Security exceptions
"""

from __future__ import annotations

from typing import Any


# ── Base ─────────────────────────────────────────────────────────────────────

class HeliosBaseException(Exception):
    """
    Root exception for all HELIOS OS platform exceptions.
    All custom exceptions inherit from this class.
    """

    def __init__(
        self,
        message: str,
        error_code: str = "HELIOS_ERROR",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(error_code={self.error_code!r}, message={self.message!r})"


# ── Infrastructure Exceptions ─────────────────────────────────────────────────

class InfrastructureException(HeliosBaseException):
    """Base for all infrastructure-layer exceptions."""


class DatabaseException(InfrastructureException):
    """Raised when a database operation fails."""

    def __init__(self, message: str, operation: str | None = None, **kwargs: Any) -> None:
        super().__init__(message, error_code="DATABASE_ERROR", **kwargs)
        self.operation = operation


class SQLiteException(DatabaseException):
    """Raised on SQLite-specific failures."""

    def __init__(self, message: str, **kwargs: Any) -> None:
        super().__init__(message, **kwargs)
        self.error_code = "SQLITE_ERROR"


class PostgreSQLException(DatabaseException):
    """Raised on PostgreSQL-specific failures."""

    def __init__(self, message: str, **kwargs: Any) -> None:
        super().__init__(message, **kwargs)
        self.error_code = "POSTGRES_ERROR"


class RedisException(InfrastructureException):
    """Raised when a Redis operation fails."""

    def __init__(self, message: str, operation: str | None = None, **kwargs: Any) -> None:
        super().__init__(message, error_code="REDIS_ERROR", **kwargs)
        self.operation = operation


class ServiceUnavailableException(InfrastructureException):
    """Raised when a downstream service is unreachable."""

    def __init__(self, service: str, **kwargs: Any) -> None:
        super().__init__(
            f"Service '{service}' is currently unavailable.",
            error_code="SERVICE_UNAVAILABLE",
            **kwargs,
        )
        self.service = service


# ── Domain / Business Exceptions ─────────────────────────────────────────────

class DomainException(HeliosBaseException):
    """Base for all business logic / domain exceptions."""


class EntityNotFoundException(DomainException):
    """Raised when a requested entity does not exist."""

    def __init__(self, entity_type: str, entity_id: str, **kwargs: Any) -> None:
        super().__init__(
            f"{entity_type} with ID '{entity_id}' was not found.",
            error_code="ENTITY_NOT_FOUND",
            **kwargs,
        )
        self.entity_type = entity_type
        self.entity_id = entity_id


class DuplicateEntityException(DomainException):
    """Raised when an entity already exists and cannot be duplicated."""

    def __init__(self, entity_type: str, field: str, value: str, **kwargs: Any) -> None:
        super().__init__(
            f"{entity_type} with {field}='{value}' already exists.",
            error_code="DUPLICATE_ENTITY",
            **kwargs,
        )


class BusinessRuleViolationException(DomainException):
    """Raised when a business rule is violated."""

    def __init__(self, rule: str, message: str, **kwargs: Any) -> None:
        super().__init__(message, error_code="BUSINESS_RULE_VIOLATION", **kwargs)
        self.rule = rule


class InvalidOperationException(DomainException):
    """Raised when an operation is not permitted in the current state."""

    def __init__(self, message: str, **kwargs: Any) -> None:
        super().__init__(message, error_code="INVALID_OPERATION", **kwargs)


# ── Security Exceptions ───────────────────────────────────────────────────────

class SecurityException(HeliosBaseException):
    """Base for all security-related exceptions."""


class AuthenticationException(SecurityException):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Authentication failed.", **kwargs: Any) -> None:
        super().__init__(message, error_code="AUTHENTICATION_FAILED", **kwargs)


class TokenExpiredException(SecurityException):
    """Raised when a JWT token has expired."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__("Token has expired.", error_code="TOKEN_EXPIRED", **kwargs)


class TokenInvalidException(SecurityException):
    """Raised when a JWT token is malformed or invalid."""

    def __init__(self, reason: str = "Invalid token.", **kwargs: Any) -> None:
        super().__init__(reason, error_code="TOKEN_INVALID", **kwargs)


class AuthorizationException(SecurityException):
    """Raised when a user lacks the required permission."""

    def __init__(
        self,
        required_permission: str | None = None,
        message: str = "You do not have permission to perform this action.",
        **kwargs: Any,
    ) -> None:
        super().__init__(message, error_code="AUTHORIZATION_DENIED", **kwargs)
        self.required_permission = required_permission


class RateLimitExceededException(SecurityException):
    """Raised when a client exceeds the rate limit."""

    def __init__(self, retry_after: int = 60, **kwargs: Any) -> None:
        super().__init__(
            f"Rate limit exceeded. Try again in {retry_after} seconds.",
            error_code="RATE_LIMIT_EXCEEDED",
            **kwargs,
        )
        self.retry_after = retry_after


# ── Validation Exceptions ─────────────────────────────────────────────────────

class ValidationException(HeliosBaseException):
    """Raised when input data fails validation."""

    def __init__(
        self,
        message: str = "Validation failed.",
        field_errors: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, error_code="VALIDATION_ERROR", **kwargs)
        self.field_errors = field_errors or []


class ConfigurationException(HeliosBaseException):
    """Raised when the application is misconfigured."""

    def __init__(self, message: str, **kwargs: Any) -> None:
        super().__init__(message, error_code="CONFIGURATION_ERROR", **kwargs)
