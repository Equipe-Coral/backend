from sqlalchemy import Column, String, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from src.core.database import Base
import uuid

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phone = Column(String(50), unique=True, nullable=False, index=True)
    first_contact_date = Column(DateTime(timezone=True), server_default=func.now())
    location_primary = Column(JSONB, nullable=True)  # {neighborhood, city, state, coordinates, formatted_address}
    status = Column(String(50), nullable=False, default='onboarding_incomplete', index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationship with interactions
    interactions = relationship("Interaction", back_populates="user")
    # Relationship with demands
    demands = relationship("Demand", back_populates="creator")
    # Relationship with supported demands
    supported_demands = relationship("DemandSupporter", back_populates="user")

    def __repr__(self):
        return f"<User(id={self.id}, phone={self.phone}, status={self.status})>"
