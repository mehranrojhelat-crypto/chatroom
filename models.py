from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean
from datetime import datetime
from database import Base

class Room(Base):
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True, index=True)
    room_code = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    room_code = Column(String, index=True, nullable=False)
    sender = Column(String, nullable=False)
    encrypted_content = Column(Text, nullable=False)
    iv = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
