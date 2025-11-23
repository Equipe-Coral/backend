from sqlalchemy import Column, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from src.core.database import Base
import uuid

class DemandSupporter(Base):
    __tablename__ = "demand_supporters"

    demand_id = Column(UUID(as_uuid=True), ForeignKey('demands.id', ondelete='CASCADE'), primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    supported_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    demand = relationship('Demand', back_populates='supporters')
    user = relationship('User', back_populates='supported_demands')
