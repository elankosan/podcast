"""Version model."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from api.database import Base


class Version(Base):
    __tablename__ = "versions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    episode_id = Column(UUID(as_uuid=True), ForeignKey("episodes.id"), nullable=False)
    version_number = Column(Integer, nullable=False)
    version_type = Column(String, nullable=False)  # research, script, translation
    content = Column(JSONB, default=dict)
    metadata = Column(JSONB, default=dict)  # language, source_version, etc.
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    episode = relationship("Episode", back_populates="versions", foreign_keys=[episode_id])
    
    def __repr__(self):
        return f"<Version(id={self.id}, type={self.version_type}, number={self.version_number})>"
