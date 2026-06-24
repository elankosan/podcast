import json
from pathlib import Path
from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.auth import get_current_user
from api.database import get_db
from api.models.user import User
from api.models.episode import Episode
from api.models.version import Version
from api.maf_integration import PodcastWorkforce

router = APIRouter()
workforce = PodcastWorkforce()


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
    
    # Fetch latest research output from trace logs
    research_output = None
    try:
        log_dir = Path("runtime_logs")
        if log_dir.exists():
            # Find latest research trace for this episode
            trace_files = sorted(
                log_dir.glob(f"trace_{episode_id}_3_*.json"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            if trace_files:
                with open(trace_files[0], "r", encoding="utf-8") as f:
                    trace = json.load(f)
                    research_output = trace.get("output", {}).get("synthesis", "")
    except Exception:
        pass
    
    episode.status = "scripting"
    db.commit()
    
    result = workforce.execute_phase(
        phase="4",
        episode_id=str(episode_id),
        vision=episode.vision,
    )
    
    # If successful, save to Version table
    if result.get("success") and result.get("output"):
        script_content = result["output"].get("script_enhanced", result["output"].get("script_raw", ""))
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
            )
            db.add(version)
            db.commit()
            
            episode.status = "scripted"
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
