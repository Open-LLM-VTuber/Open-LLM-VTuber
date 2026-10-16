"""Tests for database module."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.open_llm_vtuber.db.models import (
    Viewer,
    InsideJoke,
    ChatMessage,
    Session,
    TrollRecord,
    AudioGeneration,
)


class TestModels:
    """Tests for database models."""

    def test_viewer_model(self):
        """Test Viewer model creation."""
        viewer = Viewer(
            username="testuser",
            streams_attended=5,
            total_tips=10.5,
            nickname="Testy",
            last_seen=1234567890.0,
        )
        assert viewer.username == "testuser"
        assert viewer.streams_attended == 5
        assert viewer.total_tips == 10.5
        assert viewer.nickname == "Testy"
        assert viewer.last_seen == 1234567890.0

    def test_inside_joke_model(self):
        """Test InsideJoke model creation."""
        joke = InsideJoke(
            username="testuser",
            joke_name="the_incident",
            context="That time with the creeper",
            occurrences=3,
        )
        assert joke.username == "testuser"
        assert joke.joke_name == "the_incident"
        assert joke.context == "That time with the creeper"
        assert joke.occurrences == 3

    def test_chat_message_model(self):
        """Test ChatMessage model creation."""
        msg = ChatMessage(
            username="testuser",
            text="Hello world!",
            platform="twitch",
            timestamp=1234567890.0,
        )
        assert msg.username == "testuser"
        assert msg.text == "Hello world!"
        assert msg.platform == "twitch"
        assert msg.timestamp == 1234567890.0

    def test_session_model(self):
        """Test Session model creation."""
        session = Session(
            id="test-session-id",
            client_uid="client-123",
            character_config="default",
            history_uid="history-456",
            message_count=0,
            total_audio_duration=0.0,
        )
        assert session.id == "test-session-id"
        assert session.client_uid == "client-123"
        assert session.character_config == "default"
        assert session.history_uid == "history-456"
        assert session.message_count == 0
        assert session.total_audio_duration == 0.0

    def test_troll_record_model(self):
        """Test TrollRecord model creation."""
        record = TrollRecord(
            username="trolluser",
            message="This is troll bait",
            troll_type="bait",
            severity="high",
            verdict="guilty",
            confidence=0.95,
        )
        assert record.username == "trolluser"
        assert record.message == "This is troll bait"
        assert record.troll_type == "bait"
        assert record.severity == "high"
        assert record.verdict == "guilty"
        assert record.confidence == 0.95

    def test_audio_generation_model(self):
        """Test AudioGeneration model creation."""
        audio = AudioGeneration(
            session_id="test-session-id",
            text="Hello world",
            voice="af_bella",
            file_path="/cache/hello.wav",
            duration=2.5,
            latency_ms=150.0,
        )
        assert audio.session_id == "test-session-id"
        assert audio.text == "Hello world"
        assert audio.voice == "af_bella"
        assert audio.file_path == "/cache/hello.wav"
        assert audio.duration == 2.5
        assert audio.latency_ms == 150.0


class TestDatabaseSession:
    """Tests for database session management."""

    @pytest.mark.asyncio
    async def test_get_database_url_default(self):
        """Test default database URL."""
        from src.open_llm_vtuber.db.session import get_database_url
        url = get_database_url()
        assert url == "sqlite+aiosqlite:///data/vtuber.db"

    @pytest.mark.asyncio
    async def test_init_db_creates_tables(self):
        """Test init_db creates tables."""
        from src.open_llm_vtuber.db.session import init_db
        
        with patch("src.open_llm_vtuber.db.session.create_async_engine") as mock_create_engine:
            mock_engine = AsyncMock()
            mock_conn = AsyncMock()
            # Properly mock the async context manager
            mock_context = AsyncMock()
            mock_context.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_context.__aexit__ = AsyncMock(return_value=None)
            mock_engine.begin = MagicMock(return_value=mock_context)
            mock_create_engine.return_value = mock_engine
            
            await init_db("sqlite+aiosqlite:///./test.db")
            
            mock_create_engine.assert_called_once()
            mock_conn.run_sync.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_db(self):
        """Test close_db disposes engine."""
        import src.open_llm_vtuber.db.session as session_module
        from src.open_llm_vtuber.db.session import close_db
        
        # Mock engine
        mock_engine = AsyncMock()
        session_module._engine = mock_engine
        session_module._session_factory = MagicMock()
        
        await close_db()
        
        mock_engine.dispose.assert_called_once()
        assert session_module._engine is None
        assert session_module._session_factory is None