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


@router.post("/{episode_id}/translate")
async def translate_episode(
    episode_id: UUID,
    language: str = "fr",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Trigger MAF translation for an episode."""
    episode = db.query(Episode).filter(Episode.id == episode_id).first()
    if not episode:
        raise HTTPException(status_code=404, detail="Episode not found")

    # Fetch latest script output from the database.
    script_version = (
        db.query(Version)
        .filter(Version.episode_id == episode_id, Version.version_type == "script")
        .order_by(Version.version_number.desc())
        .first()
    )
    if not script_version:
        raise HTTPException(status_code=400, detail="No script found for this episode. Generate a script first.")

    script_content = script_version.content
    if not script_content:
        raise HTTPException(status_code=400, detail="Script content is empty.")

    episode.status = "translating"
    db.commit()

    workforce = get_workforce()
    result = workforce.execute_phase(
        phase="5",
        episode_id=str(episode_id),
        vision=episode.vision,
        language=language,
        input_data={"script": script_content},
    )

    # If successful, save to Version table
    if result.get("success") and result.get("output"):
        output = result["output"]
        translation = output.get("translation_polished", output.get("translation_raw", ""))
        if translation:
            latest = (
                db.query(Version)
                .filter(Version.episode_id == episode_id, Version.version_type == "translation")
                .order_by(Version.version_number.desc())
                .first()
            )
            next_version = (latest.version_number + 1) if latest else 1

            version = Version(
                episode_id=episode_id,
                version_number=next_version,
                version_type="translation",
                content=translation,
                metadata_json={"language": language},
                created_by=current_user.id,
            )
            db.add(version)
            db.commit()

            episode.status = "translated"
            db.commit()
    else:
        episode.status = "translation_failed"
        db.commit()

    return {
        "episode_id": str(episode_id),
        "status": episode.status,
        "language": language,
        "trace_id": result.get("trace_id"),
        "result": result,
    }


@router.get("/{episode_id}/translations")
async def get_translations(
    episode_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all translated versions for an episode."""
    translations = (
        db.query(Version)
        .filter(Version.episode_id == episode_id, Version.version_type == "translation")
        .order_by(Version.version_number.desc())
        .all()
    )

    return {
        "episode_id": str(episode_id),
        "translations": [
            {
                "version_number": t.version_number,
                "content_preview": t.content[:500] if isinstance(t.content, str) else t.content,
                "created_at": t.created_at,
            }
            for t in translations
        ],
    }
