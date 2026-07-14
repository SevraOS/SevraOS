"""
HELIOS OS + SEVRA AI
SQLCipher Encryption Layer - SECTION 9
"""

import structlog
from sqlalchemy import event
from sqlalchemy.engine import Engine
from database.config.settings import db_config

logger = structlog.get_logger(__name__)

def init_sqlcipher(engine: Engine) -> None:
    """
    Hooks into SQLAlchemy engine to provide the PRAGMA key for SQLCipher.
    Only applied if HELIOS_SQLITE_ENCRYPTION_KEY is provided in the environment.
    """
    key = db_config.SQLITE_ENCRYPTION_KEY
    
    if not key:
        if db_config.is_production:
            logger.critical("sqlite_encryption_key_missing_in_production")
            raise ValueError("HELIOS_SQLITE_ENCRYPTION_KEY is required in production.")
        else:
            logger.warning("sqlite_encryption_disabled_dev_mode")
            return

    @event.listens_for(engine, "connect")
    def connect(dbapi_connection, connection_record):
        """
        Executes PRAGMA key to decrypt the database on every new connection.
        We also set some performance pragmas here for SQLite.
        """
        try:
            cursor = dbapi_connection.cursor()
            
            # Apply decryption key
            cursor.execute(f"PRAGMA key='{key}'")
            
            # Performance tuning (WAL mode, busy timeout)
            cursor.execute(f"PRAGMA journal_mode={db_config.SQLITE_JOURNAL_MODE}")
            cursor.execute(f"PRAGMA synchronous={db_config.SQLITE_SYNCHRONOUS}")
            cursor.execute(f"PRAGMA cache_size={db_config.SQLITE_CACHE_SIZE_KB}")
            cursor.execute(f"PRAGMA busy_timeout={db_config.SQLITE_BUSY_TIMEOUT_MS}")
            
            cursor.close()
            logger.debug("sqlcipher_pragmas_applied")
        except Exception as e:
            logger.critical("sqlcipher_initialization_failed", error=str(e))
            raise

async def rotate_sqlite_key(engine: Engine, new_key: str) -> None:
    """
    Key Rotation Support (Section 9).
    Rotates the SQLCipher encryption key using PRAGMA rekey.
    This operation requires an exclusive lock and rewrites the DB.
    """
    logger.warning("initiating_sqlite_key_rotation")
    with engine.connect() as conn:
        cursor = conn.connection.cursor()
        try:
            cursor.execute(f"PRAGMA rekey='{new_key}'")
            logger.info("sqlite_key_rotation_successful")
        except Exception as e:
            logger.critical("sqlite_key_rotation_failed", error=str(e))
            raise
        finally:
            cursor.close()

