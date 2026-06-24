"""Health check endpoints for the podcast application."""

import asyncio
from typing import Dict

from fastapi import APIRouter

from api.config import settings
from api.database import engine
from api.sphere_sync import PodcastSphereSync

router = APIRouter()


async def check_postgres() -> Dict[str, str]:
    """Check PostgreSQL connection."""
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "healthy"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


async def check_redis() -> Dict[str, str]:
    """Check Redis connection."""
    try:
        import redis.asyncio as redis
        r = redis.from_url(settings.REDIS_URL)
        await r.ping()
        await r.close()
        return {"status": "healthy"}
    except ImportError:
        return {"status": "unhealthy", "error": "redis package not installed"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


async def check_neo4j() -> Dict[str, str]:
    """Check Neo4j connection."""
    try:
        sync = PodcastSphereSync()
        result = sync.health_check()
        if result.get("status") == "healthy":
            return {"status": "healthy"}
        return {"status": "unhealthy", "error": result.get("reason", "unknown")}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


@router.get("/health", tags=["health"])
async def health_check():
    """Basic health check — returns combined status of all dependencies."""
    postgres_status = await check_postgres()
    redis_status = await check_redis()
    neo4j_status = await check_neo4j()

    all_healthy = all(
        s["status"] == "healthy"
        for s in [postgres_status, redis_status, neo4j_status]
    )

    return {
        "status": "healthy" if all_healthy else "degraded",
        "services": {
            "api": {"status": "healthy"},
            "postgres": postgres_status,
            "redis": redis_status,
            "neo4j": neo4j_status,
        },
    }


@router.get("/health/live", tags=["health"])
async def liveness_check():
    """Liveness probe — indicates the API process is running."""
    return {"status": "alive", "service": "api"}


@router.get("/health/ready", tags=["health"])
async def readiness_check():
    """Readiness probe — checks all external dependencies."""
    postgres_status = await check_postgres()
    redis_status = await check_redis()
    neo4j_status = await check_neo4j()

    all_healthy = all(
        s["status"] == "healthy"
        for s in [postgres_status, redis_status, neo4j_status]
    )

    return {
        "status": "ready" if all_healthy else "not_ready",
        "services": {
            "api": {"status": "healthy"},
            "postgres": postgres_status,
            "redis": redis_status,
            "neo4j": neo4j_status,
        },
    }
