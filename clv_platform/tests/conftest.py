import os
import pytest
from fastapi.testclient import TestClient

# Set environment variable to use sqlite for testing BEFORE importing connection or models
os.environ["DATABASE_URL"] = "sqlite:///test_platform.db"

from clv_platform.database.connection import Base, engine, SessionLocal, get_db
from clv_platform.database.models import User
from clv_platform.services.auth import get_password_hash
from clv_platform.api.main import app

@pytest.fixture(scope="session", autouse=True)
def init_test_db():
    # Force sqlite tables creation
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    # Pre-populate seed users for authentication test
    db = SessionLocal()
    try:
        # Seed users if not exist
        default_users = [
            {"email": "admin@clv.com", "password": "admin123", "role": "Admin"},
            {"email": "analyst@clv.com", "password": "analyst123", "role": "Analyst"},
            {"email": "user@clv.com", "password": "user123", "role": "Business User"},
        ]
        for u_data in default_users:
            exists = db.query(User).filter(User.email == u_data["email"]).first()
            if not exists:
                db_user = User(
                    email=u_data["email"],
                    hashed_password=get_password_hash(u_data["password"]),
                    role=u_data["role"]
                )
                db.add(db_user)
        db.commit()
    finally:
        db.close()
        
    yield
    
    # Clean up test database file after session
    try:
        Base.metadata.drop_all(bind=engine)
        if os.path.exists("test_platform.db"):
            os.remove("test_platform.db")
    except Exception:
        pass

@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture
def client(db_session):
    def _get_db_override():
        try:
            yield db_session
        finally:
            pass
            
    # Override get_db dependency
    app.dependency_overrides[get_db] = _get_db_override
    with TestClient(app) as c:
        yield c
    # Clear override after test
    app.dependency_overrides.clear()
