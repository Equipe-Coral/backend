from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import settings

# Ensure we use 127.0.0.1 instead of localhost to avoid Windows/Docker resolution issues
# This is a runtime fix, but ideally should be in .env
db_url = settings.DATABASE_URL.replace("localhost", "127.0.0.1")

engine = create_engine(db_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """
    Creates all tables defined in the metadata.
    This replaces Alembic for simple setups.
    """
    # Import models here to ensure they are registered with Base
    from src.models.interaction import Interaction  # noqa
    from src.models.user import User  # noqa
    from src.models.demand import Demand  # noqa
    from src.models.demand_supporter import DemandSupporter  # noqa
    from src.models.conversation_state import ConversationState  # noqa
    from src.models.legislative_item import LegislativeItem  # noqa
    from src.models.pl_interaction import PLInteraction  # noqa

    # Configure the registry to resolve all relationships
    from sqlalchemy.orm import configure_mappers
    configure_mappers()

    # Enable pgvector extension
    from sqlalchemy import text
    with engine.connect() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        connection.commit()

    Base.metadata.create_all(bind=engine)

