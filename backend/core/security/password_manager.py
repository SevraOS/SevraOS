"""
HELIOS OS + SEVRA AI
Password Manager

Argon2id hashing for user passwords.
NEVER stores or logs plaintext passwords.
Contract: Architecture Section C4.1 — Argon2id required.
"""

from __future__ import annotations

from passlib.context import CryptContext

# Argon2id — the strongest password hashing algorithm
# As required by Architecture Contract Section C4.1
_pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto",
    argon2__memory_cost=65536,   # 64 MB
    argon2__time_cost=3,         # 3 iterations
    argon2__parallelism=4,       # 4 parallel threads
)


class PasswordManager:
    """
    Handles password hashing and verification.
    Uses Argon2id — resistant to GPU/ASIC brute-force attacks.
    """

    @staticmethod
    def hash(plain_password: str) -> str:
        """
        Hash a plaintext password using Argon2id.
        Returns the hashed string (includes salt and algorithm metadata).
        """
        return _pwd_context.hash(plain_password)

    @staticmethod
    def verify(plain_password: str, hashed_password: str) -> bool:
        """
        Verify a plaintext password against a stored Argon2id hash.
        Returns True if the password matches, False otherwise.
        Constant-time comparison — safe against timing attacks.
        """
        return _pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def needs_rehash(hashed_password: str) -> bool:
        """
        Check if a stored hash needs to be rehashed.
        Returns True if the hash was created with an older configuration.
        Call this after successful login and rehash if needed.
        """
        return _pwd_context.needs_update(hashed_password)


# ── Token Blacklist (Redis-backed) ────────────────────────────────────────────

class TokenBlacklist:
    """
    Redis-backed JWT token blacklist.
    Used to invalidate tokens on logout or security events.
    Key format: blacklist:{jti}
    TTL is set to the token's remaining expiry time.
    """

    PREFIX = "blacklist:"

    def __init__(self, redis_client: object) -> None:
        self._redis = redis_client

    async def revoke(self, jti: str, ttl_seconds: int) -> None:
        """
        Add a token JTI to the blacklist.
        The key expires automatically after TTL seconds.
        """
        key = f"{self.PREFIX}{jti}"
        await self._redis.setex(key, ttl_seconds, "revoked")  # type: ignore[attr-defined]

    async def is_revoked(self, jti: str) -> bool:
        """
        Check if a token JTI is blacklisted.
        Returns True if the token has been revoked.
        """
        key = f"{self.PREFIX}{jti}"
        result = await self._redis.exists(key)  # type: ignore[attr-defined]
        return bool(result)

    async def revoke_all_for_user(self, user_id: str, active_jtis: list[str], ttl_seconds: int) -> None:
        """
        Revoke all active tokens for a user (e.g., on password change or account lock).
        Requires a list of active JTIs — the caller is responsible for tracking these.
        """
        for jti in active_jtis:
            await self.revoke(jti, ttl_seconds)
