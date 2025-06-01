# server/models/chat.py

from sqlalchemy import Column, Integer, String, Text, DateTime
from datetime import datetime
from . import Base


class ChatLog(Base):
    __tablename__ = "chat_logs"

    id = Column(Integer, primary_key=True, index=True)
    user = Column(String, index=True)
    course = Column(String, index=True)
    session_id = Column(String, index=True)
    role = Column(String)
    message = Column(Text)
    timestamp = Column(DateTime, default=datetime.now)
    context = Column(Text, nullable=True)


class SessionTitle(Base):
    __tablename__ = "session_titles"

    id = Column(Integer, primary_key=True, index=True)
    user = Column(String, index=True)
    course = Column(String, index=True)
    session_id = Column(String, index=True)
    title = Column(String)
