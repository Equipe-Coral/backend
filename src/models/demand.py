from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from src.core.database import Base
import uuid

class Demand(Base):
    __tablename__ = "demands"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    creator_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    scope_level = Column(Integer, nullable=False)  # 1,2,3
    theme = Column(String(50), nullable=False)
    location = Column(JSONB, nullable=True)  # {address, coordinates, ...}
    affected_entity = Column(String(200), nullable=True)
    urgency = Column(String(20), nullable=False)
    supporters_count = Column(Integer, default=1)
    status = Column(String(50), default='active')
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    creator = relationship('User', back_populates='demands')
    supporters = relationship('DemandSupporter', back_populates='demand', cascade='all, delete-orphan')
    interactions = relationship('Interaction', back_populates='demand')
