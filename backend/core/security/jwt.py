"""
HELIOS OS + SEVRA AI
JWT Security Framework

RS256 asymmetric JWT issuance and validation.
Private key signs (Security Service only).
Public key validates (all services).

Contract:
  - Access token TTL: 15 minutes
  - Refresh token TTL: 7 days
  - Algorithm: RS256 with 4096-bit RSA key pair
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import structlog
from jose import JWTError, jwt
from pydantic import BaseModel, Field

from config.settings import get_settings
from core.exceptions.base import TokenExpiredException, TokenInvalidException

logger = structlog.get_logger(__name__)
settings = get_settings()


# ── Token Payload Models ──────────────────────────────────────────────────────

class TokenPayload(BaseModel):
    """Decoded JWT token payload."""

    sub: str = Field(description="User ID (subject)")
    jti: str = Field(description="JWT ID — unique token identifier")
    iat: int = Field(description="Issued at (Unix timestamp)")
    exp: int = Field(description="Expiry (Unix timestamp)")
    token_type: str = Field(description="access | refresh")
    roles: list[str] = Field(default_factory=list)
    facility_id: str | None = None
    iss: str = Field(description="Issuer")
    aud: str = Field(description="Audience")


class TokenPair(BaseModel):
    """Access + Refresh token pair returned on authentication."""

    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int = Field(description="Access token TTL in seconds")


# ── Key Management ────────────────────────────────────────────────────────────

def _load_private_key() -> str:
    """Load RS256 private key from path specified in settings."""
    if not settings.JWT_PRIVATE_KEY_PATH:
        if settings.ENVIRONMENT == "production":
            raise RuntimeError("JWT_PRIVATE_KEY_PATH is required in production")
        # Development fallback: generate or use a test key placeholder
        logger.warning("jwt_private_key_not_configured_using_dev_mode")
        return _get_dev_secret()
    path = Path(settings.JWT_PRIVATE_KEY_PATH)
    if not path.exists():
        raise RuntimeError(f"JWT private key not found at: {path}")
    return path.read_text()


def _load_public_key() -> str:
    """Load RS256 public key from path specified in settings."""
    if not settings.JWT_PUBLIC_KEY_PATH:
        if settings.ENVIRONMENT == "production":
            raise RuntimeError("JWT_PUBLIC_KEY_PATH is required in production")
        logger.warning("jwt_public_key_not_configured_using_dev_mode")
        return _get_dev_secret()
    path = Path(settings.JWT_PUBLIC_KEY_PATH)
    if not path.exists():
        raise RuntimeError(f"JWT public key not found at: {path}")
    return path.read_text()


def _get_dev_secret() -> str:
    """
    Development-only symmetric secret for HS256.
    NEVER used in production (validated in Settings).
    """
    return "DEV_ONLY_SECRET_DO_NOT_USE_IN_PRODUCTION_helios-sevra-2026"


def _get_algorithm() -> str:
    return settings.JWT_ALGORITHM


# ── Token Creation ────────────────────────────────────────────────────────────

class JWTManager:
    """
    Manages JWT token creation and validation.
    
    In production: RS256 with private/public key pair.
    In development: HS256 with dev secret for simplicity.
    """

    def __init__(self) -> None:
        self._algorithm = _get_algorithm()
        self._issuer = settings.JWT_ISSUER
        self._audience = settings.JWT_AUDIENCE
        self._access_ttl = settings.JWT_ACCESS_TOKEN_EXPIRE_SECONDS
        self._refresh_ttl = settings.JWT_REFRESH_TOKEN_EXPIRE_SECONDS

        if settings.ENVIRONMENT == "production":
            self._sign_key = _load_private_key()
            self._verify_key = _load_public_key()
        else:
            # Development: use HS256 with a simple secret
            self._algorithm = "HS256"
            self._sign_key = _get_dev_secret()
            self._verify_key = _get_dev_secret()

    def create_token_pair(
        self,
        user_id: str,
        roles: list[str],
        facility_id: str | None = None,
    ) -> TokenPair:
        """Create an access + refresh token pair for a user."""
        access_token = self._create_token(
            subject=user_id,
            token_type="access",
            ttl_seconds=self._access_ttl,
            roles=roles,
            facility_id=facility_id,
        )
        refresh_token = self._create_token(
            subject=user_id,
            token_type="refresh",
            ttl_seconds=self._refresh_ttl,
            roles=roles,
            facility_id=facility_id,
        )
        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=self._access_ttl,
        )

    def _create_token(
        self,
        subject: str,
        token_type: str,
        ttl_seconds: int,
        roles: list[str],
        facility_id: str | None = None,
    ) -> str:
        now = datetime.now(timezone.utc)
        payload: dict[str, Any] = {
            "sub": subject,
            "jti": str(uuid.uuid4()),
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(seconds=ttl_seconds)).timestamp()),
            "token_type": token_type,
            "roles": roles,
            "iss": self._issuer,
            "aud": self._audience,
        }
        if facility_id:
            payload["facility_id"] = facility_id

        return jwt.encode(payload, self._sign_key, algorithm=self._algorithm)

    def decode_token(self, token: str) -> TokenPayload:
        """
        Decode and validate a JWT token.
        Raises TokenExpiredException or TokenInvalidException on failure.
        """
        try:
            payload = jwt.decode(
                token,
                self._verify_key,
                algorithms=[self._algorithm],
                audience=self._audience,
                issuer=self._issuer,
            )
            return TokenPayload(**payload)
        except JWTError as exc:
            error_str = str(exc).lower()
            if "expired" in error_str:
                raise TokenExpiredException() from exc
            raise TokenInvalidException(reason=f"Token validation failed: {exc}") from exc

    def decode_refresh_token(self, token: str) -> TokenPayload:
        """Decode and validate a refresh token specifically."""
        payload = self.decode_token(token)
        if payload.token_type != "refresh":
            raise TokenInvalidException(reason="Expected a refresh token.")
        return payload


# ── Singleton ─────────────────────────────────────────────────────────────────

_jwt_manager: JWTManager | None = None


def get_jwt_manager() -> JWTManager:
    """Get or create the singleton JWTManager."""
    global _jwt_manager
    if _jwt_manager is None:
        _jwt_manager = JWTManager()
    return _jwt_manager
