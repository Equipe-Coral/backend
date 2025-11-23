from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from src.core.database import Base

class ConversationState(Base):
    __tablename__ = "conversation_states"

    phone = Column(String(50), primary_key=True)
    current_stage = Column(String(50), nullable=False)  # new_user, awaiting_location, confirming_location, etc
    context_data = Column(JSONB, nullable=True)  # temporary conversation context
    last_message_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<ConversationState(phone={self.phone}, stage={self.current_stage})>"
