from sqlalchemy import Column, String, Integer, Text, TIMESTAMP, text
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from datetime import datetime
from src.core.database import Base

class LegislativeItem(Base):
    """
    Legislative items (PLs, PECs, etc) from Câmara and Senado APIs

    Stores propositions with complete data for caching and analytics
    """
    __tablename__ = "legislative_items"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    external_id = Column(Text, nullable=False, unique=True, index=True)  # API ID
    source = Column(Text, nullable=False, index=True)  # 'camara' or 'senado'
    type = Column(Text, nullable=False)  # 'PL', 'PEC', 'PLP', etc
    number = Column(Text, nullable=False)
    year = Column(Integer, nullable=False, index=True)
    title = Column(Text, nullable=False)
    summary = Column(Text)
    ementa = Column(Text)  # Official full text
    status = Column(Text)
    last_update = Column(TIMESTAMP)
    themes = Column(JSONB)  # JSONB for flexible theme storage
    keywords = Column(ARRAY(Text))  # Array for fast GIN search
    full_data = Column(JSONB)  # Complete API response
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<LegislativeItem {self.title}>"

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': str(self.id),
            'external_id': self.external_id,
            'source': self.source,
            'type': self.type,
            'number': self.number,
            'year': self.year,
            'title': self.title,
            'summary': self.summary,
            'ementa': self.ementa,
            'status': self.status,
            'last_update': self.last_update.isoformat() if self.last_update else None,
            'themes': self.themes,
            'keywords': self.keywords,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
