"""
Unit tests for chat route navigation link response.

Validates Requirements 4.1 and 4.2:
- Response includes navigation_links when nav matches exist
- Response has empty navigation_links when no nav matches
"""

import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI

from src.api.chat_routes import router, init_chat_components
from src.components.rag_engine import RAGResult
from src.components.navigation_links_store import NavigationLinkEntry
from src.components.session_manager import ChatSession


def _create_app_and_client():
    """Create a fresh FastAPI app with the chat router for testing."""
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def _setup_mocks(rag_result=None, session_id="test-session-nav"):
    """Wire mocked dependencies into the chat route module."""
    mock_session_mgr = MagicMock()
    mock_rag = MagicMock()

    session = ChatSession(session_id=session_id)
    mock_session_mgr.load_or_create.return_value = session
    mock_session_mgr.get_recent_messages.return_value = []

    if rag_result is not None:
        mock_rag.generate_response.return_value = rag_result
    else:
        mock_rag.generate_response.return_value = RAGResult(response="default")

    init_chat_components(
        chromadb_client=MagicMock(),
        llm_client=MagicMock(),
        session_manager=mock_session_mgr,
        rag_engine=mock_rag,
    )
    return mock_session_mgr, mock_rag


class TestNavigationLinksInResponse:
    """Tests that the chat endpoint includes navigation_links when present."""

    def test_response_includes_navigation_links_when_matches_exist(self):
        client = _create_app_and_client()
        nav_entries = [
            NavigationLinkEntry(
                id="search",
                page_name="Search",
                route="/search",
                description="Search for similar legal cases",
                keywords=["search", "find cases"],
                roles=["user", "helper", "admin"],
            ),
            NavigationLinkEntry(
                id="dashboard",
                page_name="Dashboard",
                route="/dashboard",
                description="View your case dashboard",
                keywords=["dashboard", "my cases"],
                roles=["user", "admin"],
            ),
        ]
        rag_result = RAGResult(
            response="You can search for cases on the Search page.",
            sources=[],
            navigation_links=nav_entries,
        )
        _setup_mocks(rag_result=rag_result)

        resp = client.post("/api/chat", json={"message": "Where do I search?"})
        assert resp.status_code == 200

        data = resp.json()
        assert "navigation_links" in data
        assert len(data["navigation_links"]) == 2

        first = data["navigation_links"][0]
        assert first["page_name"] == "Search"
        assert first["route"] == "/search"
        assert first["description"] == "Search for similar legal cases"

        second = data["navigation_links"][1]
        assert second["page_name"] == "Dashboard"
        assert second["route"] == "/dashboard"
        assert second["description"] == "View your case dashboard"

    def test_response_has_empty_navigation_links_when_no_matches(self):
        client = _create_app_and_client()
        rag_result = RAGResult(
            response="Here is some legal information.",
            sources=[],
            navigation_links=[],
        )
        _setup_mocks(rag_result=rag_result)

        resp = client.post("/api/chat", json={"message": "Tell me about case law"})
        assert resp.status_code == 200

        data = resp.json()
        assert "navigation_links" in data
        assert data["navigation_links"] == []
