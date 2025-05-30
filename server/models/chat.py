# server/models/chat.py

from sqlalchemy import Column, Integer, String, Text, DateTime
from datetime import datetime
from . import Base


# -------------------------------
# Chat Log Model
# -------------------------------

class ChatLog(Base):
    """
    Database model for individual chat messages.
    Stores message role (user or assistant), content, and timestamp.
    """
    __tablename__ = "chat_logs"

    id = Column(Integer, primary_key=True, index=True)
    user = Column(String, index=True)
    course = Column(String, index=True)
    session_id = Column(String, index=True)
    role = Column(String)
    message = Column(Text)
    timestamp = Column(DateTime, default=datetime.now)
    context = Column(Text, nullable=True)


# -------------------------------
# Session Title Model
# -------------------------------

class SessionTitle(Base):
    """
    Database model for chat session metadata.
    Stores user, course, session ID, and the human-readable session title.
    """
    __tablename__ = "session_titles"

    id = Column(Integer, primary_key=True, index=True)
    user = Column(String, index=True)
    course = Column(String, index=True)
    session_id = Column(String, index=True)
    title = Column(String)
