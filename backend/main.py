"""
HELIOS OS + SEVRA AI
Uvicorn Entry Point

Run the application:
  Development:  python main.py
  Production:   uvicorn app:app --host 0.0.0.0 --port 8000 --workers 4
"""

import uvicorn

from config.settings import get_settings

settings = get_settings()


if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.ENVIRONMENT == "development",
        log_config=None,  # Structlog handles logging — disable uvicorn default
        access_log=False,  # Handled by RequestLoggingMiddleware
        workers=1 if settings.ENVIRONMENT == "development" else settings.WORKERS,
        loop="uvloop",
        http="httptools",
    )
