from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.auth import get_current_user
from api.database import get_db
from api.models.user import User
from api.models.episode import Episode
from api.sphere_sync import PodcastSphereSync

router = APIRouter()
sphere = PodcastSphereSync()


@router.post("/{episode_id}/sync")
async def sync_to_sphere(
    episode_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Sync an episode to the sphere knowledge graph."""
    episode = db.query(Episode).filter(Episode.id == episode_id).first()
    if not episode:
        raise HTTPException(status_code=404, detail="Episode not found")
    
    result = sphere.sync_episode(
        episode_id=str(episode_id),
        podcast_id=str(episode.podcast_id),
        title=episode.title,
        vision=episode.vision or "",
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Sync failed"))
    
    return result


@router.get("/related")
async def find_related(
    topic: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Find episodes related to a topic."""
    episodes = sphere.query_related_episodes(topic)
    return {"topic": topic, "episodes": episodes}


@router.get("/{episode_id}/knowledge")
async def get_episode_knowledge(
    episode_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get knowledge graph data for an episode."""
    knowledge = sphere.get_episode_knowledge(str(episode_id))
    return {"episode_id": str(episode_id), "knowledge": knowledge}


@router.get("/health")
async def sphere_health():
    """Check sphere (Neo4j) health."""
    return sphere.health_check()
