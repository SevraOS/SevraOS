"""
HELIOS OS + SEVRA AI
Global Exception Handlers

Registers FastAPI exception handlers that convert all exceptions
into the standard API error response format.
"""

from __future__ import annotations

import structlog
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import ORJSONResponse
from pydantic import ValidationError

from core.exceptions.base import (
    AuthenticationException,
    AuthorizationException,
    BusinessRuleViolationException,
    DomainException,
    DuplicateEntityException,
    EntityNotFoundException,
    HeliosBaseException,
    InfrastructureException,
    InvalidOperationException,
    RateLimitExceededException,
    TokenExpiredException,
    TokenInvalidException,
    ValidationException,
)
from core.responses.models import ErrorResponse, FieldError

logger = structlog.get_logger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    """Register all global exception handlers on the FastAPI app."""

    @app.exception_handler(RequestValidationError)
    async def request_validation_handler(
        request: Request, exc: RequestValidationError
    ) -> ORJSONResponse:
        field_errors = [
            FieldError(
                field=".".join(str(loc) for loc in err["loc"]),
                message=err["msg"],
                error_type=err["type"],
            )
            for err in exc.errors()
        ]
        logger.warning(
            "request_validation_error",
            path=str(request.url),
            error_count=len(field_errors),
        )
        return ORJSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=ErrorResponse(
                error_code="VALIDATION_ERROR",
                message="Request validation failed.",
                field_errors=field_errors,
            ).model_dump(),
        )

    @app.exception_handler(ValidationException)
    async def validation_exception_handler(
        request: Request, exc: ValidationException
    ) -> ORJSONResponse:
        logger.warning("validation_exception", error_code=exc.error_code, message=exc.message)
        return ORJSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=ErrorResponse(
                error_code=exc.error_code,
                message=exc.message,
            ).model_dump(),
        )

    @app.exception_handler(AuthenticationException)
    @app.exception_handler(TokenExpiredException)
    @app.exception_handler(TokenInvalidException)
    async def authentication_handler(
        request: Request, exc: HeliosBaseException
    ) -> ORJSONResponse:
        logger.warning(
            "authentication_failure",
            error_code=exc.error_code,
            path=str(request.url),
        )
        return ORJSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            headers={"WWW-Authenticate": "Bearer"},
            content=ErrorResponse(
                error_code=exc.error_code,
                message=exc.message,
            ).model_dump(),
        )

    @app.exception_handler(AuthorizationException)
    async def authorization_handler(
        request: Request, exc: AuthorizationException
    ) -> ORJSONResponse:
        logger.warning(
            "authorization_denied",
            error_code=exc.error_code,
            required_permission=exc.required_permission,
            path=str(request.url),
        )
        return ORJSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content=ErrorResponse(
                error_code=exc.error_code,
                message=exc.message,
            ).model_dump(),
        )

    @app.exception_handler(RateLimitExceededException)
    async def rate_limit_handler(
        request: Request, exc: RateLimitExceededException
    ) -> ORJSONResponse:
        return ORJSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            headers={"Retry-After": str(exc.retry_after)},
            content=ErrorResponse(
                error_code=exc.error_code,
                message=exc.message,
            ).model_dump(),
        )

    @app.exception_handler(EntityNotFoundException)
    async def not_found_handler(
        request: Request, exc: EntityNotFoundException
    ) -> ORJSONResponse:
        return ORJSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=ErrorResponse(
                error_code=exc.error_code,
                message=exc.message,
            ).model_dump(),
        )

    @app.exception_handler(DuplicateEntityException)
    async def duplicate_handler(
        request: Request, exc: DuplicateEntityException
    ) -> ORJSONResponse:
        return ORJSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=ErrorResponse(
                error_code=exc.error_code,
                message=exc.message,
            ).model_dump(),
        )

    @app.exception_handler(InvalidOperationException)
    @app.exception_handler(BusinessRuleViolationException)
    async def domain_error_handler(
        request: Request, exc: DomainException
    ) -> ORJSONResponse:
        logger.warning("domain_error", error_code=exc.error_code, message=exc.message)
        return ORJSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=ErrorResponse(
                error_code=exc.error_code,
                message=exc.message,
            ).model_dump(),
        )

    @app.exception_handler(InfrastructureException)
    async def infrastructure_handler(
        request: Request, exc: InfrastructureException
    ) -> ORJSONResponse:
        logger.error(
            "infrastructure_error",
            error_code=exc.error_code,
            message=exc.message,
            exc_info=True,
        )
        return ORJSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=ErrorResponse(
                error_code=exc.error_code,
                message="A platform infrastructure error occurred. Please try again.",
            ).model_dump(),
        )

    @app.exception_handler(HeliosBaseException)
    async def helios_base_handler(
        request: Request, exc: HeliosBaseException
    ) -> ORJSONResponse:
        logger.error("unhandled_helios_exception", error_code=exc.error_code, exc_info=True)
        return ORJSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse(
                error_code=exc.error_code,
                message="An unexpected platform error occurred.",
            ).model_dump(),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> ORJSONResponse:
        logger.error(
            "unhandled_exception",
            exception_type=type(exc).__name__,
            path=str(request.url),
            exc_info=True,
        )
        return ORJSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse(
                error_code="INTERNAL_SERVER_ERROR",
                message="An unexpected internal error occurred.",
            ).model_dump(),
        )
