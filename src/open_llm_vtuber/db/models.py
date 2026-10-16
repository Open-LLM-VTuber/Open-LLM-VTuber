"""Database migration models using SQLAlchemy."""

from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()


class Viewer(Base):
    """Viewer/Chatter model for Parasocial CRM."""
    __tablename__ = "viewers"

    username = Column(String(255), primary_key=True)
    streams_attended = Column(Integer, default=1)
    total_tips = Column(Float, default=0.0)
    nickname = Column(String(255), default="")
    last_seen = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    inside_jokes = relationship("InsideJoke", back_populates="viewer", cascade="all, delete-orphan")
    chat_messages = relationship("ChatMessage", back_populates="viewer", cascade="all, delete-orphan")


class InsideJoke(Base):
    """Inside joke model for Parasocial CRM."""
    __tablename__ = "inside_jokes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(255), ForeignKey("viewers.username"), nullable=False)
    joke_name = Column(String(255), nullable=False)
    context = Column(Text)
    occurrences = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    viewer = relationship("Viewer", back_populates="inside_jokes")

    __table_args__ = (
        Index("ix_inside_jokes_username", "username"),
    )


class ChatMessage(Base):
    """Chat message model for history tracking."""
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(255), ForeignKey("viewers.username"), nullable=False)
    text = Column(Text, nullable=False)
    platform = Column(String(50), default="twitch")
    timestamp = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    viewer = relationship("Viewer", back_populates="chat_messages")

    __table_args__ = (
        Index("ix_chat_messages_username", "username"),
        Index("ix_chat_messages_timestamp", "timestamp"),
    )


class Session(Base):
    """Session model for tracking user sessions."""
    __tablename__ = "sessions"

    id = Column(String(36), primary_key=True)  # UUID
    client_uid = Column(String(36), nullable=False)
    character_config = Column(String(255))
    history_uid = Column(String(36))
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    message_count = Column(Integer, default=0)
    total_audio_duration = Column(Float, default=0.0)

    __table_args__ = (
        Index("ix_sessions_client_uid", "client_uid"),
    )


class TrollRecord(Base):
    """Troll detection record model."""
    __tablename__ = "troll_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    troll_type = Column(String(50), nullable=False)
    severity = Column(String(20), nullable=False)
    verdict = Column(String(50), nullable=False)
    confidence = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_troll_records_username", "username"),
        Index("ix_troll_records_created_at", "created_at"),
    )


class AudioGeneration(Base):
    """TTS audio generation record."""
    __tablename__ = "audio_generations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(36), ForeignKey("sessions.id"), nullable=True)
    text = Column(Text, nullable=False)
    voice = Column(String(100))
    file_path = Column(String(512))
    duration = Column(Float)
    latency_ms = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_audio_generations_session_id", "session_id"),
        Index("ix_audio_generations_created_at", "created_at"),
    )