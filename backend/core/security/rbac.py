"""
HELIOS OS + SEVRA AI
RBAC (Role-Based Access Control) Framework

Defines clinical roles, permissions, and enforcement decorators.
Roles are aligned with the Architecture Contract Section C4.2.
"""

from __future__ import annotations

from enum import Enum
from functools import wraps
from typing import Any, Callable

import structlog
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from core.exceptions.base import AuthenticationException, AuthorizationException
from core.security.jwt import JWTManager, TokenPayload, get_jwt_manager

logger = structlog.get_logger(__name__)
bearer_scheme = HTTPBearer(auto_error=False)


# ── Role Definitions ──────────────────────────────────────────────────────────

class Role(str, Enum):
    """
    HELIOS platform clinical roles.
    Contract: Architecture Section C4.2 — 6 roles exactly.
    """

    ADMIN = "admin"
    CLINICIAN = "clinician"
    NURSE = "nurse"
    DEVICE_OPERATOR = "device_operator"
    AUDITOR = "auditor"
    AI_REVIEWER = "ai_reviewer"


# ── Permission Definitions ────────────────────────────────────────────────────

class Permission(str, Enum):
    """
    Fine-grained permissions mapped to roles.
    Each endpoint declares the minimum required permission.
    """

    # Patient data
    READ_PATIENT_VITALS = "read:patient_vitals"
    READ_PATIENT_HISTORY = "read:patient_history"
    WRITE_CLINICAL_NOTES = "write:clinical_notes"

    # Alerts
    READ_AI_ALERTS = "read:ai_alerts"
    ACKNOWLEDGE_ALERTS = "acknowledge:alerts"
    REVIEW_AI_INSIGHTS = "review:ai_insights"
    APPROVE_AI_MODELS = "approve:ai_models"

    # Devices
    READ_DEVICES = "read:devices"
    REGISTER_DEVICE = "register:device"
    CONFIGURE_DEVICE = "configure:device"

    # Administration
    MANAGE_USERS = "manage:users"
    MANAGE_ROLES = "manage:roles"
    MANAGE_FACILITY = "manage:facility"

    # Audit
    READ_AUDIT_LOGS = "read:audit_logs"
    READ_SYSTEM_REPORTS = "read:system_reports"

    # System (admin only)
    READ_ALL = "read:all"
    WRITE_ALL = "write:all"


# ── Role-to-Permission Mapping ────────────────────────────────────────────────

ROLE_PERMISSIONS: dict[Role, set[Permission]] = {
    Role.ADMIN: {
        Permission.READ_ALL,
        Permission.WRITE_ALL,
        Permission.READ_PATIENT_VITALS,
        Permission.READ_PATIENT_HISTORY,
        Permission.WRITE_CLINICAL_NOTES,
        Permission.READ_AI_ALERTS,
        Permission.ACKNOWLEDGE_ALERTS,
        Permission.READ_DEVICES,
        Permission.REGISTER_DEVICE,
        Permission.CONFIGURE_DEVICE,
        Permission.MANAGE_USERS,
        Permission.MANAGE_ROLES,
        Permission.MANAGE_FACILITY,
        Permission.READ_AUDIT_LOGS,
        Permission.READ_SYSTEM_REPORTS,
    },
    Role.CLINICIAN: {
        Permission.READ_PATIENT_VITALS,
        Permission.READ_PATIENT_HISTORY,
        Permission.WRITE_CLINICAL_NOTES,
        Permission.READ_AI_ALERTS,
        Permission.ACKNOWLEDGE_ALERTS,
        Permission.READ_DEVICES,
    },
    Role.NURSE: {
        Permission.READ_PATIENT_VITALS,
        Permission.WRITE_CLINICAL_NOTES,
        Permission.READ_AI_ALERTS,
        Permission.ACKNOWLEDGE_ALERTS,
        Permission.READ_DEVICES,
    },
    Role.DEVICE_OPERATOR: {
        Permission.READ_DEVICES,
        Permission.REGISTER_DEVICE,
        Permission.CONFIGURE_DEVICE,
    },
    Role.AUDITOR: {
        Permission.READ_AUDIT_LOGS,
        Permission.READ_SYSTEM_REPORTS,
    },
    Role.AI_REVIEWER: {
        Permission.READ_AI_ALERTS,
        Permission.REVIEW_AI_INSIGHTS,
        Permission.APPROVE_AI_MODELS,
        Permission.READ_SYSTEM_REPORTS,
    },
}


# ── Permission Checker ────────────────────────────────────────────────────────

class RBACChecker:
    """Evaluates permissions for a given set of user roles."""

    @staticmethod
    def get_permissions_for_roles(roles: list[str]) -> set[Permission]:
        """Return the union of all permissions granted to the given roles."""
        permissions: set[Permission] = set()
        for role_str in roles:
            try:
                role = Role(role_str)
                permissions |= ROLE_PERMISSIONS.get(role, set())
            except ValueError:
                logger.warning("unknown_role_encountered", role=role_str)
        return permissions

    @staticmethod
    def has_permission(roles: list[str], required: Permission) -> bool:
        """Check if any of the given roles grants the required permission."""
        granted = RBACChecker.get_permissions_for_roles(roles)
        # Admin with READ_ALL or WRITE_ALL bypasses specific checks
        if Permission.READ_ALL in granted or Permission.WRITE_ALL in granted:
            return True
        return required in granted

    @staticmethod
    def has_role(user_roles: list[str], required_role: Role) -> bool:
        """Check if the user has a specific role."""
        return required_role.value in user_roles


# ── FastAPI Dependency: Current User ──────────────────────────────────────────

async def get_current_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    jwt_manager: JWTManager = Depends(get_jwt_manager),
) -> TokenPayload:
    """
    FastAPI dependency: extracts and validates the Bearer JWT token.
    Raises AuthenticationException if token is missing or invalid.
    """
    if credentials is None:
        raise AuthenticationException("Authorization header is required.")

    return jwt_manager.decode_token(credentials.credentials)


async def get_current_user(
    token: TokenPayload = Depends(get_current_token),
) -> TokenPayload:
    """
    FastAPI dependency: returns the validated token payload (current user context).
    Use this in any endpoint that requires authentication.
    """
    if token.token_type != "access":
        raise AuthenticationException("An access token is required.")
    return token


# ── Permission Dependency Factory ─────────────────────────────────────────────

def require_permission(permission: Permission) -> Callable[..., Any]:
    """
    FastAPI dependency factory.
    Returns a dependency that requires the specified permission.
    
    Usage:
        @router.get("/patients", dependencies=[Depends(require_permission(Permission.READ_PATIENT_VITALS))])
    """

    async def _check(token: TokenPayload = Depends(get_current_user)) -> TokenPayload:
        if not RBACChecker.has_permission(token.roles, permission):
            logger.warning(
                "permission_denied",
                user_id=token.sub,
                required=permission.value,
                user_roles=token.roles,
            )
            raise AuthorizationException(required_permission=permission.value)
        return token

    return _check


def require_role(role: Role) -> Callable[..., Any]:
    """
    FastAPI dependency factory.
    Returns a dependency that requires the specified role.
    
    Usage:
        @router.delete("/users/{id}", dependencies=[Depends(require_role(Role.ADMIN))])
    """

    async def _check(token: TokenPayload = Depends(get_current_user)) -> TokenPayload:
        if not RBACChecker.has_role(token.roles, role):
            logger.warning(
                "role_required_denied",
                user_id=token.sub,
                required_role=role.value,
                user_roles=token.roles,
            )
            raise AuthorizationException(
                required_permission=role.value,
                message=f"Role '{role.value}' is required.",
            )
        return token

    return _check
