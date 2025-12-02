from sqlalchemy import Column, String, DateTime, JSON, Boolean, Text, ARRAY
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from src.core.database import Base
import uuid

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phone = Column(String(50), unique=True, nullable=False, index=True)
    
    # Authentication fields
    name = Column(String(255), nullable=True)
    email = Column(String(255), unique=True, nullable=True, index=True)
    cpf = Column(String(11), unique=True, nullable=True, index=True)
    password_hash = Column(String(255), nullable=True)
    is_verified = Column(Boolean, default=False, nullable=False, index=True)
    
    # Location fields
    uf = Column(String(2), nullable=True)
    city = Column(String(100), nullable=True)
    address = Column(String(255), nullable=True)
    number = Column(String(20), nullable=True)
    
    # Profile fields
    bio = Column(Text, nullable=True)
    avatar_url = Column(String(512), nullable=True)
    interests = Column(ARRAY(String), nullable=True)
    
    # Legacy/chatbot fields
    first_contact_date = Column(DateTime(timezone=True), server_default=func.now())
    location_primary = Column(JSONB, nullable=True)  # {neighborhood, city, state, coordinates, formatted_address}
    status = Column(String(50), nullable=False, default='onboarding_incomplete', index=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    interactions = relationship("Interaction", back_populates="user")
    demands = relationship("Demand", back_populates="creator")
    supported_demands = relationship("DemandSupporter", back_populates="user")

    def __repr__(self):
        return f"<User(id={self.id}, phone={self.phone}, email={self.email}, status={self.status})>"
