import os
from datetime import datetime, timedelta
from typing import Optional, List
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from clv_platform.database.connection import get_db
from clv_platform.database.models import User

# JWT Secret and Configurations
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "clv_platform_super_secret_jwt_key_2026")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    return user

class RoleChecker:
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted. Role required: one of {self.allowed_roles}",
            )
        return current_user

# Predefined role dependencies
require_admin = RoleChecker(["Admin"])
require_analyst_or_above = RoleChecker(["Admin", "Analyst"])
require_any_user = RoleChecker(["Admin", "Analyst", "Business User"])

def seed_default_users(db: Session):
    """Seed base users in database if they don't exist yet."""
    default_users = [
        {"email": "admin@clv.com", "password": "admin123", "role": "Admin"},
        {"email": "analyst@clv.com", "password": "analyst123", "role": "Analyst"},
        {"email": "user@clv.com", "password": "user123", "role": "Business User"},
    ]
    
    for u_data in default_users:
        exists = db.query(User).filter(User.email == u_data["email"]).first()
        if not exists:
            hashed = get_password_hash(u_data["password"])
            db_user = User(
                email=u_data["email"],
                hashed_password=hashed,
                role=u_data["role"]
            )
            db.add(db_user)
            db.commit()
            db.refresh(db_user)
