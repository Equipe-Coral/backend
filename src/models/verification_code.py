from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from src.core.database import Base

class VerificationCode(Base):
    __tablename__ = "verification_codes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), nullable=False, index=True)
    code = Column(String(6), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<VerificationCode(email={self.email}, code={self.code}, expires_at={self.expires_at})>"
