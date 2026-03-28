"""
Session Manager for RAG Chatbot

Manages JSON file-based session persistence for chat conversations.
Sessions are stored as individual JSON files in the configured sessions directory.
"""

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from src.config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class ChatSession:
    """Represents a chat session with conversation history."""

    session_id: str
    user_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    messages: List[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Serialize session to a dictionary."""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "messages": self.messages,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ChatSession":
        """Deserialize session from a dictionary."""
        return cls(
            session_id=data["session_id"],
            user_id=data.get("user_id"),
            created_at=datetime.fromisoformat(data["created_at"]),
            last_activity=datetime.fromisoformat(data["last_activity"]),
            messages=data.get("messages", []),
        )


class SessionManager:
    """Manages chat session persistence using JSON files."""

    def __init__(self, sessions_dir: Optional[str] = None):
        self.sessions_dir = Path(sessions_dir) if sessions_dir else settings.CHAT_SESSIONS_DIR
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    def load_or_create(self, session_id: Optional[str] = None) -> ChatSession:
        """Load an existing session by ID, or create a new one.

        If session_id is provided and a corresponding file exists, load it.
        If the file is corrupted, log a warning and create a new session.
        Otherwise, create a new session.
        """
        if session_id:
            session_path = self.sessions_dir / f"{session_id}.json"
            if session_path.exists():
                try:
                    return self._load(session_id)
                except (json.JSONDecodeError, KeyError, ValueError) as e:
                    logger.warning(
                        "Corrupted session file %s, creating new session: %s",
                        session_id,
                        e,
                    )
        return self._create()

    def save(self, session: ChatSession) -> None:
        """Persist a session to its JSON file."""
        path = self.sessions_dir / f"{session.session_id}.json"
        path.write_text(json.dumps(session.to_dict(), default=str))

    def append_messages(
        self, session: ChatSession, user_msg: str, assistant_msg: str
    ) -> None:
        """Append a user + assistant message pair to the session and update last_activity."""
        now = datetime.utcnow()
        session.messages.append(
            {"role": "user", "content": user_msg, "timestamp": now.isoformat()}
        )
        session.messages.append(
            {"role": "assistant", "content": assistant_msg, "timestamp": now.isoformat()}
        )
        session.last_activity = now

    def get_recent_messages(
        self, session: ChatSession, max_messages: Optional[int] = None
    ) -> List[dict]:
        """Return the most recent messages from the session.

        If max_messages is None, uses settings.MAX_HISTORY_MESSAGES.
        """
        if max_messages is None:
            max_messages = settings.MAX_HISTORY_MESSAGES
        return session.messages[-max_messages:]

    def _load(self, session_id: str) -> ChatSession:
        """Load a session from its JSON file."""
        path = self.sessions_dir / f"{session_id}.json"
        data = json.loads(path.read_text())
        return ChatSession.from_dict(data)

    def _create(self) -> ChatSession:
        """Create a new empty session with a fresh UUID."""
        return ChatSession(session_id=str(uuid.uuid4()))
