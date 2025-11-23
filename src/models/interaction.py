from sqlalchemy import Column, String, Text, Float, DateTime, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from src.core.database import Base
import uuid

class Interaction(Base):
    __tablename__ = "interactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phone = Column(String(50), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True, index=True)
    message_type = Column(String(20), nullable=False, index=True)  # 'text', 'audio', 'image'
    original_message = Column(Text, nullable=True)
    transcription = Column(Text, nullable=True)
    audio_duration_seconds = Column(Float, nullable=True)
    classification = Column(String(50), nullable=True, index=True)  # 'ONBOARDING', 'DEMANDA', 'DUVIDA', 'OUTRO'
    extracted_data = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Relationship with user
    user = relationship("User", back_populates="interactions")
