"""Unit tests for SessionManager and ChatSession."""

import json
import uuid
from datetime import datetime
from pathlib import Path

import pytest

from src.components.session_manager import ChatSession, SessionManager


@pytest.fixture
def tmp_sessions_dir(tmp_path):
    """Provide a temporary directory for session files."""
    sessions_dir = tmp_path / "chat_sessions"
    sessions_dir.mkdir()
    return sessions_dir


@pytest.fixture
def manager(tmp_sessions_dir):
    """Provide a SessionManager using a temp directory."""
    return SessionManager(sessions_dir=str(tmp_sessions_dir))


class TestChatSession:
    def test_to_dict_round_trip(self):
        now = datetime.utcnow()
        session = ChatSession(
            session_id="abc-123",
            user_id="user1",
            created_at=now,
            last_activity=now,
            messages=[{"role": "user", "content": "hi", "timestamp": now.isoformat()}],
        )
        d = session.to_dict()
        restored = ChatSession.from_dict(d)
        assert restored.session_id == session.session_id
        assert restored.user_id == session.user_id
        assert restored.created_at == session.created_at
        assert restored.last_activity == session.last_activity
        assert restored.messages == session.messages

    def test_to_dict_keys(self):
        session = ChatSession(session_id="x")
        d = session.to_dict()
        assert set(d.keys()) == {"session_id", "user_id", "created_at", "last_activity", "messages"}

    def test_from_dict_missing_optional_fields(self):
        data = {
            "session_id": "s1",
            "created_at": "2026-01-01T00:00:00",
            "last_activity": "2026-01-01T00:00:00",
        }
        session = ChatSession.from_dict(data)
        assert session.user_id is None
        assert session.messages == []


class TestSessionManager:
    def test_create_new_session_when_no_id(self, manager):
        session = manager.load_or_create(None)
        assert session.session_id
        uuid.UUID(session.session_id)  # validates it's a valid UUID
        assert session.messages == []

    def test_create_new_session_when_id_not_found(self, manager):
        session = manager.load_or_create("nonexistent-id")
        assert session.session_id != "nonexistent-id"

    def test_save_and_load(self, manager, tmp_sessions_dir):
        session = manager.load_or_create(None)
        session.messages.append({"role": "user", "content": "hello", "timestamp": datetime.utcnow().isoformat()})
        manager.save(session)

        loaded = manager.load_or_create(session.session_id)
        assert loaded.session_id == session.session_id
        assert len(loaded.messages) == 1
        assert loaded.messages[0]["content"] == "hello"

    def test_save_creates_json_file(self, manager, tmp_sessions_dir):
        session = manager.load_or_create(None)
        manager.save(session)
        path = tmp_sessions_dir / f"{session.session_id}.json"
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["session_id"] == session.session_id

    def test_corrupted_session_creates_new(self, manager, tmp_sessions_dir):
        bad_id = str(uuid.uuid4())
        bad_path = tmp_sessions_dir / f"{bad_id}.json"
        bad_path.write_text("not valid json {{{")

        session = manager.load_or_create(bad_id)
        # Should get a new session, not the corrupted one
        assert session.session_id != bad_id
        assert session.messages == []

    def test_append_messages(self, manager):
        session = manager.load_or_create(None)
        assert len(session.messages) == 0

        manager.append_messages(session, "hi there", "hello!")
        assert len(session.messages) == 2
        assert session.messages[0]["role"] == "user"
        assert session.messages[0]["content"] == "hi there"
        assert session.messages[1]["role"] == "assistant"
        assert session.messages[1]["content"] == "hello!"
        assert "timestamp" in session.messages[0]
        assert "timestamp" in session.messages[1]

    def test_append_messages_updates_last_activity(self, manager):
        session = manager.load_or_create(None)
        old_activity = session.last_activity
        manager.append_messages(session, "q", "a")
        assert session.last_activity >= old_activity

    def test_get_recent_messages_returns_all_when_fewer(self, manager):
        session = manager.load_or_create(None)
        manager.append_messages(session, "q1", "a1")
        recent = manager.get_recent_messages(session, max_messages=10)
        assert len(recent) == 2

    def test_get_recent_messages_truncates(self, manager):
        session = manager.load_or_create(None)
        for i in range(10):
            manager.append_messages(session, f"q{i}", f"a{i}")
        assert len(session.messages) == 20
        recent = manager.get_recent_messages(session, max_messages=4)
        assert len(recent) == 4
        # Should be the last 4 messages
        assert recent[0]["content"] == "q8"
        assert recent[1]["content"] == "a8"
        assert recent[2]["content"] == "q9"
        assert recent[3]["content"] == "a9"

    def test_sessions_dir_created_if_missing(self, tmp_path):
        new_dir = tmp_path / "new" / "sessions"
        assert not new_dir.exists()
        SessionManager(sessions_dir=str(new_dir))
        assert new_dir.exists()
