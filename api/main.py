from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from api.config import settings
from api.database import engine, Base
from api.auth import get_current_user
from api.routers import auth, podcasts, episodes, users, health, research, script, translation, sphere, metrics


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure tables exist (safe for dev; alembic is used for production migrations)
    Base.metadata.create_all(bind=engine)
    yield
    # Shutdown: cleanup
    pass


app = FastAPI(
    title="Multi-Lingual Podcast API",
    description="Intelligent podcast preparation studio",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(health.router, tags=["health"])
app.include_router(metrics.router, prefix="/api/metrics", tags=["metrics"])
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(users.router, prefix="/api/admin", tags=["admin"])
app.include_router(podcasts.router, prefix="/api/podcasts", tags=["podcasts"])
app.include_router(episodes.router, prefix="/api/episodes", tags=["episodes"])
app.include_router(research.router, prefix="/api/research", tags=["research"])
app.include_router(script.router, prefix="/api/scripts", tags=["scripts"])
app.include_router(translation.router, prefix="/api/translations", tags=["translations"])
app.include_router(sphere.router, prefix="/api/sphere", tags=["sphere"])


@app.get("/")
async def root():
    return {"message": "Multi-Lingual Podcast API", "version": "1.0.0"}
