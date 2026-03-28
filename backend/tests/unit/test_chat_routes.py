"""
Unit tests for the chat API routes.
"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI

from src.api.chat_routes import (
    router,
    init_chat_components,
    ChatRequest,
    ChatResponse,
    DocumentSourceResponse,
    ChatErrorResponse,
)
from src.components.rag_engine import RAGResult, DocumentSource
from src.components.session_manager import ChatSession


def _create_app_and_client():
    """Create a fresh FastAPI app with the chat router for testing."""
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def _setup_mocks(
    rag_response="Test answer",
    rag_sources=None,
    rag_side_effect=None,
    session_id="test-session-123",
):
    """Wire mocked dependencies into the chat route module."""
    mock_chromadb = MagicMock()
    mock_llm = MagicMock()
    mock_session_mgr = MagicMock()
    mock_rag = MagicMock()

    session = ChatSession(session_id=session_id)
    mock_session_mgr.load_or_create.return_value = session
    mock_session_mgr.get_recent_messages.return_value = []

    if rag_side_effect:
        mock_rag.generate_response.side_effect = rag_side_effect
    else:
        sources = rag_sources or []
        mock_rag.generate_response.return_value = RAGResult(
            response=rag_response, sources=sources
        )

    init_chat_components(
        chromadb_client=mock_chromadb,
        llm_client=mock_llm,
        session_manager=mock_session_mgr,
        rag_engine=mock_rag,
    )
    return mock_chromadb, mock_llm, mock_session_mgr, mock_rag


class TestChatEndpointSuccess:
    """Happy-path tests for POST /api/chat."""

    def test_returns_200_with_valid_message(self):
        client = _create_app_and_client()
        _setup_mocks()

        resp = client.post("/api/chat", json={"message": "Hello"})
        assert resp.status_code == 200

    def test_response_contains_session_id(self):
        client = _create_app_and_client()
        _setup_mocks(session_id="abc-123")

        data = client.post("/api/chat", json={"message": "Hi"}).json()
        assert data["session_id"] == "abc-123"

    def test_response_contains_llm_answer(self):
        client = _create_app_and_client()
        _setup_mocks(rag_response="Legal answer here")

        data = client.post("/api/chat", json={"message": "question"}).json()
        assert data["response"] == "Legal answer here"

    def test_response_contains_sources(self):
        client = _create_app_and_client()
        sources = [
            DocumentSource(
                case_id="CASE-001",
                title="Title",
                snippet="snippet text",
                relevance_score=0.85,
            )
        ]
        _setup_mocks(rag_sources=sources)

        data = client.post("/api/chat", json={"message": "query"}).json()
        assert len(data["sources"]) == 1
        assert data["sources"][0]["case_id"] == "CASE-001"

    def test_passes_session_id_to_session_manager(self):
        client = _create_app_and_client()
        _, _, mock_sm, _ = _setup_mocks()

        client.post("/api/chat", json={"session_id": "my-sess", "message": "hi"})
        mock_sm.load_or_create.assert_called_once_with("my-sess")

    def test_passes_none_session_id_when_omitted(self):
        client = _create_app_and_client()
        _, _, mock_sm, _ = _setup_mocks()

        client.post("/api/chat", json={"message": "hi"})
        mock_sm.load_or_create.assert_called_once_with(None)

    def test_persists_session_after_response(self):
        client = _create_app_and_client()
        _, _, mock_sm, _ = _setup_mocks()

        client.post("/api/chat", json={"message": "hi"})
        mock_sm.append_messages.assert_called_once()
        mock_sm.save.assert_called_once()


class TestChatEndpointEmptyMessage:
    """Tests for empty / whitespace-only message rejection (Req 3.5)."""

    def test_whitespace_only_returns_400(self):
        client = _create_app_and_client()
        _setup_mocks()

        resp = client.post("/api/chat", json={"message": "   "})
        assert resp.status_code == 400
        assert resp.json()["error_code"] == "EMPTY_MESSAGE"

    def test_empty_string_returns_422_via_pydantic(self):
        """Pydantic min_length=1 rejects truly empty strings before our handler."""
        client = _create_app_and_client()
        _setup_mocks()

        resp = client.post("/api/chat", json={"message": ""})
        assert resp.status_code == 422

    def test_missing_message_returns_422(self):
        client = _create_app_and_client()
        _setup_mocks()

        resp = client.post("/api/chat", json={})
        assert resp.status_code == 422


class TestChatEndpointInternalError:
    """Tests for 500 error handling (Req 3.6)."""

    def test_rag_exception_returns_500(self):
        client = _create_app_and_client()
        _setup_mocks(rag_side_effect=RuntimeError("boom"))

        resp = client.post("/api/chat", json={"message": "test"})
        assert resp.status_code == 500
        body = resp.json()
        assert body["error"] is True
        assert body["error_code"] == "INTERNAL_ERROR"

    def test_500_response_has_timestamp(self):
        client = _create_app_and_client()
        _setup_mocks(rag_side_effect=Exception("fail"))

        body = client.post("/api/chat", json={"message": "test"}).json()
        assert "timestamp" in body


class TestPydanticModels:
    """Sanity checks on the Pydantic models themselves."""

    def test_chat_request_valid(self):
        req = ChatRequest(message="hello")
        assert req.session_id is None
        assert req.message == "hello"

    def test_chat_request_with_session(self):
        req = ChatRequest(session_id="abc", message="hi")
        assert req.session_id == "abc"

    def test_document_source_response(self):
        ds = DocumentSourceResponse(
            case_id="C1", title="T", snippet="S", relevance_score=0.9
        )
        assert ds.case_id == "C1"

    def test_chat_error_response_defaults(self):
        err = ChatErrorResponse(
            message="bad", error_code="ERR", timestamp="2025-01-01T00:00:00"
        )
        assert err.error is True
