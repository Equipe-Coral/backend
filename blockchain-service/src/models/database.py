"""
Modelos de banco de dados para tracking de transações blockchain.
Usa SQLAlchemy para persistência local.
"""

import uuid
from datetime import datetime
from typing import Generator

from sqlalchemy import (
    Column,
    String,
    Integer,
    DateTime,
    Text,
    create_engine,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

from src.config import settings


Base = declarative_base()


class BlockchainRecord(Base):
    """
    Registro de transações enviadas para a blockchain.
    Permite rastrear o status e histórico de todas as tokenizações.
    """

    __tablename__ = "blockchain_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Tipo e dados
    tipo = Column(String(50), nullable=False, index=True)
    data_hash = Column(String(64), nullable=False, unique=True, index=True)
    original_data = Column(JSONB, nullable=False)

    # Blockchain info
    tx_hash = Column(String(66), unique=True, index=True)
    block_number = Column(Integer)
    network = Column(String(50), nullable=False)
    contract_address = Column(String(42))

    # Status tracking
    status = Column(String(20), nullable=False, default="pending")
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)

    # Gas info
    gas_used = Column(Integer)
    gas_price_gwei = Column(Integer)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    submitted_at = Column(DateTime)
    confirmed_at = Column(DateTime)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<BlockchainRecord(tipo={self.tipo}, status={self.status}, tx_hash={self.tx_hash})>"


# Database setup
def get_engine():
    """Cria engine do SQLAlchemy com tratamento de localhost."""
    db_url = settings.DATABASE_URL.replace("localhost", "127.0.0.1")
    return create_engine(db_url, pool_pre_ping=True)


engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Inicializa o banco de dados criando as tabelas."""
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency para injeção de sessão do banco de dados.
    Uso com FastAPI: db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
