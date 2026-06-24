"""Episode model."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from api.database import Base


class Episode(Base):
    __tablename__ = "episodes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    podcast_id = Column(UUID(as_uuid=True), ForeignKey("podcasts.id"), nullable=False)
    title = Column(String, nullable=False)
    vision = Column(Text)
    status = Column(String, default="draft")  # draft, researching, scripting, translating, published
    current_version_id = Column(UUID(as_uuid=True), ForeignKey("versions.id", use_alter=True, name="fk_episodes_current_version"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    podcast = relationship("Podcast", back_populates="episodes")
    versions = relationship("Version", back_populates="episode", cascade="all, delete-orphan", foreign_keys="Version.episode_id")
    
    def __repr__(self):
        return f"<Episode(id={self.id}, title={self.title}, status={self.status})>"
