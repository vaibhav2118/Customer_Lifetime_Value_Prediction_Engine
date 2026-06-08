import os
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

log = logging.getLogger(__name__)

# Default Database connection configurations
# DB URL structure: postgresql://username:password@host:port/database
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/clv_db"
)

# Use SQLite as fallback if PostgreSQL is not available or database connection fails
# This makes it easy for testing without Docker or Postgres running.
IS_SQLITE = False

try:
    log.info("Testing connection to database: %s", DATABASE_URL.split("@")[-1] if "@" in DATABASE_URL else DATABASE_URL)
    engine = create_engine(
        DATABASE_URL, 
        pool_pre_ping=True,
        connect_args={"connect_timeout": 5} if "postgresql" in DATABASE_URL else {}
    )
    # Test connection
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    log.info("Successfully connected to database.")
    if "sqlite" in DATABASE_URL:
        IS_SQLITE = True
except Exception as e:
    log.warning("PostgreSQL connection failed: %s. Falling back to SQLite local database.", e)
    # Create sqlite db in project directory
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sqlite_db_path = os.path.join(PROJECT_ROOT, "outputs", "local_platform.db")
    os.makedirs(os.path.dirname(sqlite_db_path), exist_ok=True)
    DATABASE_URL = f"sqlite:///{sqlite_db_path}"
    log.info("Using SQLite database at %s", sqlite_db_path)
    engine = create_engine(
        DATABASE_URL, 
        connect_args={"check_same_thread": False}
    )
    IS_SQLITE = True

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """Dependency for obtaining database session in FastAPI routes."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initializes schema and tables."""
    from clv_platform.database.models import User # Ensure models are loaded
    
    if IS_SQLITE:
        log.info("Creating SQLite tables if they do not exist...")
        Base.metadata.create_all(bind=engine)
    else:
        log.info("Creating PostgreSQL tables if they do not exist...")
        # For Postgres, Base.metadata.create_all will work. Let's make sure it does.
        Base.metadata.create_all(bind=engine)
    log.info("Database initialized successfully.")
