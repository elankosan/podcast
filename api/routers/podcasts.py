from uuid import UUID
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.auth import get_current_user
from api.database import get_db
from api.models.user import User
from api.models.podcast import Podcast
from api.models.episode import Episode

router = APIRouter()


@router.get("/")
async def list_podcasts(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    podcasts = db.query(Podcast).filter(Podcast.owner_id == current_user.id).all()
    return [{"id": str(p.id), "title": p.title, "description": p.description, "language": p.language} for p in podcasts]


@router.post("/")
async def create_podcast(data: dict, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    podcast = Podcast(
        title=data["title"],
        description=data.get("description", ""),
        language=data.get("language", "en"),
        target_languages=data.get("target_languages", []),
        owner_id=current_user.id,
    )
    db.add(podcast)
    db.commit()
    db.refresh(podcast)
    return {"id": str(podcast.id), "title": podcast.title}


@router.get("/{podcast_id}")
async def get_podcast(podcast_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    podcast = db.query(Podcast).filter(Podcast.id == podcast_id, Podcast.owner_id == current_user.id).first()
    if not podcast:
        raise HTTPException(status_code=404, detail="Podcast not found")
    episodes = [{"id": str(e.id), "title": e.title, "status": e.status} for e in podcast.episodes]
    return {"id": str(podcast.id), "title": podcast.title, "description": podcast.description, "episodes": episodes}


@router.put("/{podcast_id}")
async def update_podcast(podcast_id: UUID, data: dict, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    podcast = db.query(Podcast).filter(Podcast.id == podcast_id, Podcast.owner_id == current_user.id).first()
    if not podcast:
        raise HTTPException(status_code=404, detail="Podcast not found")
    podcast.title = data.get("title", podcast.title)
    podcast.description = data.get("description", podcast.description)
    db.commit()
    return {"id": str(podcast.id), "title": podcast.title}


@router.delete("/{podcast_id}")
async def delete_podcast(podcast_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    podcast = db.query(Podcast).filter(Podcast.id == podcast_id, Podcast.owner_id == current_user.id).first()
    if not podcast:
        raise HTTPException(status_code=404, detail="Podcast not found")
    db.delete(podcast)
    db.commit()
    return {"status": "deleted"}


@router.post("/{podcast_id}/episodes")
async def create_episode(podcast_id: UUID, data: dict, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    podcast = db.query(Podcast).filter(Podcast.id == podcast_id, Podcast.owner_id == current_user.id).first()
    if not podcast:
        raise HTTPException(status_code=404, detail="Podcast not found")
    episode = Episode(
        podcast_id=podcast.id,
        title=data["title"],
        vision=data.get("vision", ""),
    )
    db.add(episode)
    db.commit()
    db.refresh(episode)
    return {"id": str(episode.id), "title": episode.title, "status": episode.status}
