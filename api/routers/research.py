from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.auth import get_current_user
from api.database import get_db
from api.models.user import User
from api.models.episode import Episode
from api.maf_integration import PodcastWorkforce

router = APIRouter()
workforce = PodcastWorkforce()


@router.post("/{episode_id}/research")
async def trigger_research(
    episode_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Trigger MAF research workflow for an episode."""
    episode = db.query(Episode).filter(Episode.id == episode_id).first()
    if not episode:
        raise HTTPException(status_code=404, detail="Episode not found")
    
    # Update status
    episode.status = "researching"
    db.commit()
    
    # Execute MAF Phase 3 (Research)
    result = workforce.execute_phase(
        phase="3",
        episode_id=str(episode_id),
        vision=episode.vision,
        podcast_id=str(episode.podcast_id),
    )
    
    return {
        "episode_id": str(episode_id),
        "status": "researching",
        "trace_id": result.get("trace_id"),
        "result": result,
    }


@router.get("/{episode_id}/research")
async def get_research(
    episode_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get research status and results for an episode."""
    episode = db.query(Episode).filter(Episode.id == episode_id).first()
    if not episode:
        raise HTTPException(status_code=404, detail="Episode not found")
    
    # Get cost report
    cost_report = workforce.get_cost_report(str(episode_id))
    
    return {
        "episode_id": str(episode_id),
        "status": episode.status,
        "vision": episode.vision,
        "cost": cost_report,
    }
