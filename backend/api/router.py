"""
HELIOS OS + SEVRA AI
API Router — Versioned Router Registration

Aggregates all versioned API routers.
Future v2 routers plug in here without modifying existing v1 routes.
"""

from fastapi import APIRouter

from api.v1.router import v1_router

api_router = APIRouter()

# ── v1 ─────────────────────────────────────────────────────────────────────
api_router.include_router(v1_router)

# ── v2 (future — uncomment when ready) ──────────────────────────────────────
# from api.v2.router import v2_router
# api_router.include_router(v2_router)
