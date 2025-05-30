# server/models/user.py

from sqlalchemy import Column, Integer, String
from . import Base


# -------------------------------
# User Model
# -------------------------------

class User(Base):
    """
    Database model for application users.
    Stores username and hashed password for authentication.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
