
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text
from app.database import Base


class Room(Base):
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True, index=True)
    room_code = Column(String(16), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    room_code = Column(String(16), index=True, nullable=False)
    sender = Column(String(64), nullable=False)
    encrypted_content = Column(Text, nullable=False)
    iv = Column(String(64), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)