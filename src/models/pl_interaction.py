from sqlalchemy import Column, String, Text, TIMESTAMP, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
from src.core.database import Base

class PLInteraction(Base):
    """
    User interactions with legislative items

    Tracks when users view, support, or comment on PLs
    Used for analytics and recommendation systems
    """
    __tablename__ = "pl_interactions"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    pl_id = Column(UUID(as_uuid=True), ForeignKey('legislative_items.id', ondelete='CASCADE'), nullable=False, index=True)
    interaction_type = Column(Text, nullable=False)  # 'view', 'support', 'comment'
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    # Relationships - using string names to avoid circular imports
    # user = relationship("User", backref="pl_interactions")
    # legislative_item = relationship("LegislativeItem", backref="interactions")

    def __repr__(self):
        return f"<PLInteraction user={self.user_id} pl={self.pl_id} type={self.interaction_type}>"

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': str(self.id),
            'user_id': str(self.user_id),
            'pl_id': str(self.pl_id),
            'interaction_type': self.interaction_type,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
