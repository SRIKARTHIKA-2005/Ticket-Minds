from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from backend.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)  # "client" or "engineer"
    preferred_language = Column(String, default="en")  # "en", "es", "ta", "hi", "fr", "de"

    # Relationships
    tickets = relationship("Ticket", back_populates="client")
    messages = relationship("Message", back_populates="sender")


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(String, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    status = Column(String, default="open")  # "open", "resolved"
    priority = Column(String, default="medium")  # "low", "medium", "high"
    sentiment = Column(String, default="neutral")  # "positive", "neutral", "negative"
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    client = relationship("User", back_populates="tickets")
    messages = relationship("Message", back_populates="ticket", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(String, ForeignKey("tickets.id"), nullable=False)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    sender_role = Column(String, nullable=False)  # "client" or "engineer"
    original_text = Column(Text, nullable=False)
    translated_text = Column(Text, nullable=False)  # Translated text (to English or client language)
    language = Column(String, nullable=False)  # Detected client lang or target engineer lang
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    ticket = relationship("Ticket", back_populates="messages")
    sender = relationship("User", back_populates="messages")
