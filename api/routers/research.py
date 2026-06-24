from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.auth import get_current_user
from api.database import get_db
from api.maf_integration import get_workforce
from api.models.user import User
from api.models.episode import Episode
from api.models.version import Version

router = APIRouter()


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
    workforce = get_workforce()
    result = workforce.execute_phase(
        phase="3",
        episode_id=str(episode_id),
        vision=episode.vision,
        podcast_id=str(episode.podcast_id),
    )

    if result.get("success") and result.get("output"):
        output = result["output"]
        # Persist research output as a version so downstream agents can read it.
        latest = (
            db.query(Version)
            .filter(Version.episode_id == episode_id, Version.version_type == "research")
            .order_by(Version.version_number.desc())
            .first()
        )
        next_version = (latest.version_number + 1) if latest else 1
        version = Version(
            episode_id=episode_id,
            version_number=next_version,
            version_type="research",
            content=output,
            created_by=current_user.id,
        )
        db.add(version)

        episode.status = "researched"
        db.commit()
    else:
        episode.status = "research_failed"
        db.commit()

    return {
        "episode_id": str(episode_id),
        "status": episode.status,
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

    research_version = (
        db.query(Version)
        .filter(Version.episode_id == episode_id, Version.version_type == "research")
        .order_by(Version.version_number.desc())
        .first()
    )

    workforce = get_workforce()
    cost_report = workforce.get_cost_report(str(episode_id))

    return {
        "episode_id": str(episode_id),
        "status": episode.status,
        "vision": episode.vision,
        "research": research_version.content if research_version else None,
        "cost": cost_report,
    }
