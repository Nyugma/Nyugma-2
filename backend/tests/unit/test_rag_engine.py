"""
Unit tests for RAGEngine.
"""

import pytest
from unittest.mock import MagicMock

from src.components.chromadb_client import QueryResult
from src.components.rag_engine import (
    RAGEngine,
    RAGResult,
    DocumentSource,
    SYSTEM_PROMPT,
    NO_RESULTS_ADDENDUM,
    FALLBACK_RESPONSE,
)


def _make_query_result(n=2):
    """Helper to build a QueryResult with n fake chunks."""
    return QueryResult(
        documents=[f"Document text {i}" for i in range(n)],
        metadatas=[
            {"case_id": f"CASE-{i:03d}", "title": f"Case Title {i}"} for i in range(n)
        ],
        distances=[0.2 * (i + 1) for i in range(n)],
    )


def _make_engine(query_result=None, llm_response="LLM answer", query_side_effect=None):
    """Create a RAGEngine with mocked dependencies."""
    mock_chromadb = MagicMock()
    if query_side_effect:
        mock_chromadb.query.side_effect = query_side_effect
    else:
        mock_chromadb.query.return_value = query_result or _make_query_result()

    mock_llm = MagicMock()
    mock_llm.chat.return_value = llm_response

    engine = RAGEngine(mock_chromadb, mock_llm, max_context_chunks=5)
    return engine, mock_chromadb, mock_llm


class TestRAGEngineInit:
    def test_uses_provided_max_context_chunks(self):
        engine = RAGEngine(MagicMock(), MagicMock(), max_context_chunks=3)
        assert engine.max_context_chunks == 3

    def test_defaults_max_context_chunks_from_settings(self):
        engine = RAGEngine(MagicMock(), MagicMock())
        # settings.MAX_CONTEXT_CHUNKS defaults to 5
        assert engine.max_context_chunks == 5


class TestGenerateResponse:
    def test_returns_rag_result(self):
        engine, _, _ = _make_engine(llm_response="Test response")
        result = engine.generate_response("hello", [])

        assert isinstance(result, RAGResult)
        assert result.response == "Test response"

    def test_queries_chromadb_with_message(self):
        engine, mock_chromadb, _ = _make_engine()
        engine.generate_response("contract dispute", [])

        mock_chromadb.query.assert_called_once_with("contract dispute", n_results=5)

    def test_calls_llm_with_built_prompt(self):
        engine, _, mock_llm = _make_engine()
        engine.generate_response("test query", [])

        mock_llm.chat.assert_called_once()
        messages = mock_llm.chat.call_args[0][0]
        # Should have system prompt, context, and user message at minimum
        assert len(messages) >= 3

    def test_includes_history_in_prompt(self):
        engine, _, mock_llm = _make_engine()
        history = [
            {"role": "user", "content": "previous question"},
            {"role": "assistant", "content": "previous answer"},
        ]
        engine.generate_response("follow up", history)

        messages = mock_llm.chat.call_args[0][0]
        roles = [m["role"] for m in messages]
        contents = [m["content"] for m in messages]
        assert "previous question" in contents
        assert "previous answer" in contents

    def test_extracts_sources_from_query_result(self):
        qr = _make_query_result(2)
        engine, _, _ = _make_engine(query_result=qr)
        result = engine.generate_response("test", [])

        assert len(result.sources) == 2
        assert all(isinstance(s, DocumentSource) for s in result.sources)
        assert result.sources[0].case_id == "CASE-000"
        assert result.sources[1].case_id == "CASE-001"

    def test_source_relevance_score_computed(self):
        qr = QueryResult(
            documents=["doc"],
            metadatas=[{"case_id": "C1", "title": "T1"}],
            distances=[0.3],
        )
        engine, _, _ = _make_engine(query_result=qr)
        result = engine.generate_response("test", [])

        assert result.sources[0].relevance_score == round(1.0 - 0.3, 4)

    def test_source_snippet_truncated_to_200(self):
        long_doc = "x" * 500
        qr = QueryResult(
            documents=[long_doc],
            metadatas=[{"case_id": "C1", "title": "T1"}],
            distances=[0.1],
        )
        engine, _, _ = _make_engine(query_result=qr)
        result = engine.generate_response("test", [])

        assert len(result.sources[0].snippet) == 200


class TestNoResults:
    def test_no_results_adds_addendum_to_system_prompt(self):
        empty_qr = QueryResult(documents=[], metadatas=[], distances=[])
        engine, _, mock_llm = _make_engine(query_result=empty_qr)
        engine.generate_response("obscure query", [])

        messages = mock_llm.chat.call_args[0][0]
        system_msg = messages[0]
        assert system_msg["role"] == "system"
        assert NO_RESULTS_ADDENDUM.strip() in system_msg["content"]

    def test_no_results_returns_empty_sources(self):
        empty_qr = QueryResult(documents=[], metadatas=[], distances=[])
        engine, _, _ = _make_engine(query_result=empty_qr)
        result = engine.generate_response("obscure query", [])

        assert result.sources == []


class TestChromaDBFailure:
    def test_returns_fallback_on_chromadb_exception(self):
        engine, _, _ = _make_engine(query_side_effect=ConnectionError("DB down"))
        result = engine.generate_response("test", [])

        assert result.response == FALLBACK_RESPONSE
        assert result.sources == []

    def test_does_not_call_llm_on_chromadb_failure(self):
        engine, _, mock_llm = _make_engine(query_side_effect=Exception("fail"))
        engine.generate_response("test", [])

        mock_llm.chat.assert_not_called()


class TestLLMFailure:
    def test_raises_on_llm_exception(self):
        engine, _, mock_llm = _make_engine()
        mock_llm.chat.side_effect = Exception("OpenAI error")

        with pytest.raises(Exception, match="OpenAI error"):
            engine.generate_response("test", [])


class TestBuildPrompt:
    def test_prompt_structure_with_context(self):
        qr = _make_query_result(1)
        engine, _, mock_llm = _make_engine(query_result=qr)
        history = [{"role": "user", "content": "hi"}]
        engine.generate_response("new question", history)

        messages = mock_llm.chat.call_args[0][0]
        # system prompt, context, history user msg, current user msg
        assert messages[0]["role"] == "system"
        assert SYSTEM_PROMPT in messages[0]["content"]
        assert messages[1]["role"] == "system"  # context
        assert "Relevant legal case context" in messages[1]["content"]
        assert messages[2] == {"role": "user", "content": "hi"}
        assert messages[3] == {"role": "user", "content": "new question"}

    def test_prompt_without_context_has_no_context_message(self):
        empty_qr = QueryResult(documents=[], metadatas=[], distances=[])
        engine, _, mock_llm = _make_engine(query_result=empty_qr)
        engine.generate_response("question", [])

        messages = mock_llm.chat.call_args[0][0]
        # system prompt (with addendum) + user message only
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1] == {"role": "user", "content": "question"}
