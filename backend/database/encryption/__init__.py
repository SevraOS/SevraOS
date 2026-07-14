"""
HELIOS OS + SEVRA AI
Encryption Layer

Handles SQLCipher integration for SQLite and secure initialization.
"""

from database.encryption.sqlcipher import init_sqlcipher

__all__ = [
    "init_sqlcipher",
]
