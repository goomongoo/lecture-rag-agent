# server/api/auth.py

import os
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, status, Depends, Body
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from passlib.context import CryptContext
from jose import JWTError, jwt
from pydantic import BaseModel
from dotenv import load_dotenv
from sqlalchemy.orm import Session

from database import get_db
from models.user import User as UserModel


# -------------------------------
# Environment & Configuration
# -------------------------------

# Load environment variables from .env
load_dotenv()

# JWT configuration
SECRET_KEY = os.getenv('JWT_SECRET_KEY')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# Initialize FastAPI router
router = APIRouter()

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# -------------------------------
# Pydantic Schemas
# -------------------------------

class Token(BaseModel):
    """
    Response model for JWT token.
    """
    access_token: str
    token_type: str


class User(BaseModel):
    """
    Response model for user information.
    """
    username: str


# -------------------------------
# Utility Functions
# -------------------------------

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plaintext password against a hashed password.
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Returns a bcrypt hash of the given password.
    """
    return pwd_context.hash(password)


def authenticate_user(db: Session, username: str, password: str):
    """
    Authenticates a user by verifying their credentials.
    Returns the user object if valid, otherwise None.
    """
    user = db.query(UserModel).filter(UserModel.username == username).first()
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """
    Creates a JWT token with optional expiration.
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# -------------------------------
# Authentication Endpoints
# -------------------------------

@router.post("/token", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Authenticates user credentials and returns a JWT token.
    """
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}


# OAuth2 dependency to extract and decode token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    """
    Extracts and validates the user identity from a JWT token.
    Raises an exception if token is invalid or expired.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials"
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise credentials_exception
        return username
    except JWTError:
        raise credentials_exception


@router.get("/users/me", response_model=User)
def read_users_me(current_user: str = Depends(get_current_user)):
    """
    Returns the current authenticated user's information.
    """
    return {"username": current_user}


# -------------------------------
# Registration Endpoint
# -------------------------------

@router.post("/register")
def register(username: str = Body(...), password: str = Body(...), db: Session = Depends(get_db)):
    """
    Registers a new user with the given username and password.
    Returns an error if the username already exists.
    """
    user_exists = db.query(UserModel).filter(UserModel.username == username).first()
    if user_exists:
        raise HTTPException(status_code=400, detail="이미 존재하는 사용자입니다.")
    hashed = get_password_hash(password)
    new_user = UserModel(username=username, hashed_password=hashed)
    db.add(new_user)
    db.commit()
    return {"message": "회원가입 성공"}
