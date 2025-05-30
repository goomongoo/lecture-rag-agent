# server/database.py

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base
from models import user, chat


# -------------------------------
# Database Engine & Session Setup
# -------------------------------

# Create a SQLite engine (file-based)
engine = create_engine(
    "sqlite:///./data/app.db",
    connect_args={"check_same_thread": False}  # Required for SQLite multithreaded access
)

# Create a session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


# -------------------------------
# Database Utility Functions
# -------------------------------

def init_db():
    """
    Initializes the database by creating all defined tables.
    """
    Base.metadata.create_all(bind=engine)


def get_db():
    """
    Yields a database session for use in FastAPI dependencies.
    Ensures the session is properly closed after use.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_engine():
    """
    Returns the SQLAlchemy engine instance.
    Useful for direct access (e.g., LangGraph checkpointing).
    """
    return engine
