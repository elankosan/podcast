from uuid import UUID
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.auth import get_current_user
from api.database import get_db
from api.models.user import User
from api.models.episode import Episode
from api.models.podcast import Podcast
from api.models.version import Version

router = APIRouter()


@router.get("/")
async def list_episodes(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """List episodes belonging to the current user's podcasts."""
    episodes = (
        db.query(Episode)
        .join(Podcast, Episode.podcast_id == Podcast.id)
        .filter(Podcast.owner_id == current_user.id)
        .all()
    )
    return [{"id": str(e.id), "title": e.title, "status": e.status, "podcast_id": str(e.podcast_id)} for e in episodes]


@router.get("/{episode_id}")
async def get_episode(episode_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    episode = (
        db.query(Episode)
        .join(Podcast, Episode.podcast_id == Podcast.id)
        .filter(Episode.id == episode_id, Podcast.owner_id == current_user.id)
        .first()
    )
    if not episode:
        raise HTTPException(status_code=404, detail="Episode not found")
    return {
        "id": str(episode.id),
        "title": episode.title,
        "vision": episode.vision,
        "status": episode.status,
        "podcast_id": str(episode.podcast_id),
    }


@router.put("/{episode_id}")
async def update_episode(episode_id: UUID, data: dict, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    episode = (
        db.query(Episode)
        .join(Podcast, Episode.podcast_id == Podcast.id)
        .filter(Episode.id == episode_id, Podcast.owner_id == current_user.id)
        .first()
    )
    if not episode:
        raise HTTPException(status_code=404, detail="Episode not found")
    episode.title = data.get("title", episode.title)
    episode.vision = data.get("vision", episode.vision)
    episode.status = data.get("status", episode.status)
    db.commit()
    return {"id": str(episode.id), "title": episode.title, "status": episode.status}


@router.delete("/{episode_id}")
async def delete_episode(episode_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    episode = (
        db.query(Episode)
        .join(Podcast, Episode.podcast_id == Podcast.id)
        .filter(Episode.id == episode_id, Podcast.owner_id == current_user.id)
        .first()
    )
    if not episode:
        raise HTTPException(status_code=404, detail="Episode not found")
    db.delete(episode)
    db.commit()
    return {"status": "deleted"}


@router.get("/{episode_id}/versions")
async def list_versions(episode_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    episode = (
        db.query(Episode)
        .join(Podcast, Episode.podcast_id == Podcast.id)
        .filter(Episode.id == episode_id, Podcast.owner_id == current_user.id)
        .first()
    )
    if not episode:
        raise HTTPException(status_code=404, detail="Episode not found")
    versions = db.query(Version).filter(Version.episode_id == episode_id).order_by(Version.version_number.desc()).all()
    return [{"id": str(v.id), "type": v.version_type, "number": v.version_number} for v in versions]


@router.post("/{episode_id}/versions")
async def create_version(episode_id: UUID, data: dict, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    episode = (
        db.query(Episode)
        .join(Podcast, Episode.podcast_id == Podcast.id)
        .filter(Episode.id == episode_id, Podcast.owner_id == current_user.id)
        .first()
    )
    if not episode:
        raise HTTPException(status_code=404, detail="Episode not found")

    max_version = db.query(Version).filter(Version.episode_id == episode_id).count()
    version = Version(
        episode_id=episode_id,
        version_number=max_version + 1,
        version_type=data.get("version_type", "script"),
        content=data.get("content", {}),
        created_by=current_user.id,
    )
    db.add(version)
    db.commit()
    db.refresh(version)
    return {"id": str(version.id), "number": version.version_number, "type": version.version_type}
