"""
Unit tests for RAGEngine navigation integration.

Tests the navigation link detection path, ChromaDB fallback, prompt construction,
and exception handling when NavigationLinksStore is involved.

Requirements: 3.1, 3.2, 3.3, 3.4, 3.5
"""

import pytest
from unittest.mock import MagicMock, patch

from src.components.chromadb_client import QueryResult
from src.components.navigation_links_store import NavigationLinkEntry
from src.components.rag_engine import RAGEngine, RAGResult, SYSTEM_PROMPT


def _make_nav_entry(id="search", page_name="Search", route="/search",
                    description="Search for similar legal cases",
                    keywords=None, roles=None):
    """Helper to build a NavigationLinkEntry."""
    return NavigationLinkEntry(
        id=id,
        page_name=page_name,
        route=route,
        description=description,
        keywords=keywords or ["search", "find cases"],
        roles=roles or ["user", "helper", "admin"],
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


def _make_engine(nav_matches=None, nav_side_effect=None,
                 query_result=None, llm_response="LLM answer"):
    """Create a RAGEngine with mocked dependencies including navigation store."""
    mock_chromadb = MagicMock()
    mock_chromadb.query.return_value = query_result or _make_query_result()

    mock_llm = MagicMock()
    mock_llm.chat.return_value = llm_response

    mock_nav_store = MagicMock()
    if nav_side_effect:
        mock_nav_store.search.side_effect = nav_side_effect
    else:
        mock_nav_store.search.return_value = nav_matches if nav_matches is not None else []

    engine = RAGEngine(mock_chromadb, mock_llm, max_context_chunks=5,
                       navigation_store=mock_nav_store)
    return engine, mock_chromadb, mock_llm, mock_nav_store


class TestNavigationQueryTriggersNavPath:
    """Test that navigation query triggers nav path with mocked store.

    When the store returns matches, RAGResult should have navigation_links
    and ChromaDB should not be called.
    """

    def test_nav_matches_returns_navigation_links_in_result(self):
        nav_entries = [_make_nav_entry()]
        engine, mock_chromadb, mock_llm, _ = _make_engine(nav_matches=nav_entries)

        result = engine.generate_response("where do I search for cases?", [])

        assert isinstance(result, RAGResult)
        assert len(result.navigation_links) == 1
        assert result.navigation_links[0].page_name == "Search"
        assert result.navigation_links[0].route == "/search"

    def test_nav_matches_does_not_call_chromadb(self):
        nav_entries = [_make_nav_entry()]
        engine, mock_chromadb, _, _ = _make_engine(nav_matches=nav_entries)

        engine.generate_response("where do I search for cases?", [])

        mock_chromadb.query.assert_not_called()

    def test_nav_matches_calls_llm(self):
        nav_entries = [_make_nav_entry()]
        engine, _, mock_llm, _ = _make_engine(nav_matches=nav_entries)

        engine.generate_response("where do I search?", [])

        mock_llm.chat.assert_called_once()

    def test_nav_matches_returns_llm_response(self):
        nav_entries = [_make_nav_entry()]
        engine, _, _, _ = _make_engine(nav_matches=nav_entries, llm_response="Go to Search page")

        result = engine.generate_response("where do I search?", [])

        assert result.response == "Go to Search page"

    def test_nav_matches_returns_empty_sources(self):
        nav_entries = [_make_nav_entry()]
        engine, _, _, _ = _make_engine(nav_matches=nav_entries)

        result = engine.generate_response("where do I search?", [])

        assert result.sources == []

    def test_multiple_nav_matches_all_returned(self):
        nav_entries = [
            _make_nav_entry(id="search", page_name="Search", route="/search"),
            _make_nav_entry(id="dashboard", page_name="Dashboard", route="/dashboard"),
        ]
        engine, mock_chromadb, _, _ = _make_engine(nav_matches=nav_entries)

        result = engine.generate_response("where do I find my dashboard or search?", [])

        assert len(result.navigation_links) == 2
        mock_chromadb.query.assert_not_called()


class TestNonNavigationQueryTriggersChromaDB:
    """Test that non-navigation query triggers ChromaDB path.

    When the store returns empty, ChromaDB should be called and
    navigation_links should be empty.
    """

    def test_no_nav_matches_calls_chromadb(self):
        engine, mock_chromadb, _, _ = _make_engine(nav_matches=[])

        engine.generate_response("tell me about contract disputes", [])

        mock_chromadb.query.assert_called_once_with("tell me about contract disputes", n_results=5)

    def test_no_nav_matches_returns_empty_navigation_links(self):
        engine, _, _, _ = _make_engine(nav_matches=[])

        result = engine.generate_response("tell me about contract disputes", [])

        assert result.navigation_links == []

    def test_no_nav_matches_returns_sources_from_chromadb(self):
        qr = _make_query_result(2)
        engine, _, _, _ = _make_engine(nav_matches=[], query_result=qr)

        result = engine.generate_response("contract dispute", [])

        assert len(result.sources) == 2
        assert result.sources[0].case_id == "CASE-000"

    def test_no_nav_store_uses_chromadb_path(self):
        """When navigation_store is None, ChromaDB path is used."""
        mock_chromadb = MagicMock()
        mock_chromadb.query.return_value = _make_query_result()
        mock_llm = MagicMock()
        mock_llm.chat.return_value = "answer"

        engine = RAGEngine(mock_chromadb, mock_llm, max_context_chunks=5,
                           navigation_store=None)
        result = engine.generate_response("test query", [])

        mock_chromadb.query.assert_called_once()
        assert result.navigation_links == []


class TestPromptConstructionIncludesNavigationContext:
    """Test that prompt construction includes navigation context.

    Page names and routes should appear in the prompt sent to the LLM.
    """

    def test_prompt_contains_page_name_and_route(self):
        nav_entries = [_make_nav_entry(page_name="Search", route="/search",
                                       description="Search for similar legal cases")]
        engine, _, mock_llm, _ = _make_engine(nav_matches=nav_entries)

        engine.generate_response("where do I search?", [])

        messages = mock_llm.chat.call_args[0][0]
        # Find the navigation context message
        nav_context = messages[1]["content"]
        assert "Search" in nav_context
        assert "/search" in nav_context
        assert "Search for similar legal cases" in nav_context

    def test_prompt_contains_all_matched_pages(self):
        nav_entries = [
            _make_nav_entry(id="search", page_name="Search", route="/search",
                            description="Search for cases"),
            _make_nav_entry(id="inquiry", page_name="Inquiry", route="/inquiry",
                            description="Submit an inquiry"),
        ]
        engine, _, mock_llm, _ = _make_engine(nav_matches=nav_entries)

        engine.generate_response("search or inquiry?", [])

        messages = mock_llm.chat.call_args[0][0]
        nav_context = messages[1]["content"]
        assert "Search" in nav_context
        assert "/search" in nav_context
        assert "Inquiry" in nav_context
        assert "/inquiry" in nav_context

    def test_prompt_starts_with_system_prompt(self):
        nav_entries = [_make_nav_entry()]
        engine, _, mock_llm, _ = _make_engine(nav_matches=nav_entries)

        engine.generate_response("where do I search?", [])

        messages = mock_llm.chat.call_args[0][0]
        assert messages[0]["role"] == "system"
        assert SYSTEM_PROMPT in messages[0]["content"]

    def test_prompt_includes_history_and_user_message(self):
        nav_entries = [_make_nav_entry()]
        engine, _, mock_llm, _ = _make_engine(nav_matches=nav_entries)
        history = [
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
        ]

        engine.generate_response("where do I search?", history)

        messages = mock_llm.chat.call_args[0][0]
        contents = [m["content"] for m in messages]
        assert "hi" in contents
        assert "hello" in contents
        assert "where do I search?" in contents

    def test_nav_context_mentions_navigating_platform(self):
        nav_entries = [_make_nav_entry()]
        engine, _, mock_llm, _ = _make_engine(nav_matches=nav_entries)

        engine.generate_response("where do I search?", [])

        messages = mock_llm.chat.call_args[0][0]
        nav_context = messages[1]["content"]
        assert "navigating the platform" in nav_context.lower()


class TestNavigationStoreExceptionFallsBackToChromaDB:
    """Test that NavigationLinksStore exception falls back to ChromaDB.

    When store.search raises an exception, the ChromaDB path should be used.
    """

    def test_store_exception_falls_back_to_chromadb(self):
        engine, mock_chromadb, _, _ = _make_engine(
            nav_side_effect=RuntimeError("store broken")
        )

        result = engine.generate_response("where do I search?", [])

        mock_chromadb.query.assert_called_once()
        assert result.navigation_links == []

    def test_store_exception_returns_chromadb_sources(self):
        qr = _make_query_result(1)
        engine, _, _, _ = _make_engine(
            nav_side_effect=RuntimeError("store broken"),
            query_result=qr,
        )

        result = engine.generate_response("where do I search?", [])

        assert len(result.sources) == 1
        assert result.sources[0].case_id == "CASE-000"

    def test_store_exception_still_calls_llm(self):
        engine, _, mock_llm, _ = _make_engine(
            nav_side_effect=ValueError("bad state")
        )

        engine.generate_response("where do I search?", [])

        mock_llm.chat.assert_called_once()
