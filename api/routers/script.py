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


@router.post("/{episode_id}/script")
async def generate_script(
    episode_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Trigger MAF script generation for an episode."""
    episode = db.query(Episode).filter(Episode.id == episode_id).first()
    if not episode:
        raise HTTPException(status_code=404, detail="Episode not found")

    # Fetch latest research output from the database.
    research_version = (
        db.query(Version)
        .filter(Version.episode_id == episode_id, Version.version_type == "research")
        .order_by(Version.version_number.desc())
        .first()
    )
    if not research_version:
        raise HTTPException(status_code=400, detail="No research found for this episode. Run research first.")

    research_content = research_version.content
    if isinstance(research_content, dict):
        synthesis = research_content.get("synthesis", "")
    else:
        synthesis = str(research_content)

    if not synthesis:
        raise HTTPException(status_code=400, detail="Research synthesis is empty.")

    episode.status = "scripting"
    db.commit()

    workforce = get_workforce()
    result = workforce.execute_phase(
        phase="4",
        episode_id=str(episode_id),
        vision=episode.vision,
        input_data={"synthesis": synthesis},
    )

    # If successful, save to Version table
    if result.get("success") and result.get("output"):
        output = result["output"]
        script_content = output.get("script_enhanced", output.get("script_raw", ""))
        if script_content:
            latest = (
                db.query(Version)
                .filter(Version.episode_id == episode_id, Version.version_type == "script")
                .order_by(Version.version_number.desc())
                .first()
            )
            next_version = (latest.version_number + 1) if latest else 1

            version = Version(
                episode_id=episode_id,
                version_number=next_version,
                version_type="script",
                content=script_content,
                created_by=current_user.id,
            )
            db.add(version)
            db.commit()

            episode.status = "scripted"
            db.commit()
    else:
        episode.status = "script_failed"
        db.commit()

    return {
        "episode_id": str(episode_id),
        "status": episode.status,
        "trace_id": result.get("trace_id"),
        "result": result,
    }


@router.get("/{episode_id}/script")
async def get_script(
    episode_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the latest script version for an episode."""
    script = (
        db.query(Version)
        .filter(Version.episode_id == episode_id, Version.version_type == "script")
        .order_by(Version.version_number.desc())
        .first()
    )

    if not script:
        raise HTTPException(status_code=404, detail="No script found")

    return {
        "episode_id": str(episode_id),
        "version_number": script.version_number,
        "version_type": script.version_type,
        "content": script.content,
        "created_at": script.created_at,
    }
