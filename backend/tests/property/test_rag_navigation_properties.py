"""
Property-based tests for RAGEngine navigation integration.

Uses Hypothesis to verify correctness properties from the chatbot-navigation-links design.
"""

from typing import List
from unittest.mock import MagicMock, PropertyMock

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from src.components.rag_engine import RAGEngine, RAGResult
from src.components.navigation_links_store import NavigationLinkEntry
from src.components.chromadb_client import QueryResult


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

def _nav_entry_strategy() -> st.SearchStrategy[NavigationLinkEntry]:
    """Generate a random NavigationLinkEntry."""
    return st.builds(
        NavigationLinkEntry,
        id=st.text(
            alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789-"),
            min_size=1,
            max_size=15,
        ),
        page_name=st.text(min_size=1, max_size=30).filter(lambda s: s.strip()),
        route=st.text(
            alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz-_/"),
            min_size=1,
            max_size=20,
        ).map(lambda s: "/" + s),
        description=st.text(min_size=1, max_size=60).filter(lambda s: s.strip()),
        keywords=st.lists(
            st.text(
                alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz "),
                min_size=1,
                max_size=15,
            ).filter(lambda s: s.strip()),
            min_size=1,
            max_size=5,
        ),
        roles=st.lists(
            st.sampled_from(["user", "helper", "admin", "public"]),
            min_size=1,
            max_size=3,
            unique=True,
        ),
    )


def _user_message_strategy() -> st.SearchStrategy[str]:
    """Generate a random user message string."""
    return st.text(min_size=1, max_size=80).filter(lambda s: s.strip())


def _history_strategy() -> st.SearchStrategy[List[dict]]:
    """Generate a conversation history list."""
    return st.lists(
        st.fixed_dictionaries({
            "role": st.sampled_from(["user", "assistant"]),
            "content": st.text(min_size=1, max_size=40).filter(lambda s: s.strip()),
        }),
        min_size=0,
        max_size=3,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_chromadb():
    """Create a mock ChromaDB client that returns a valid QueryResult."""
    mock = MagicMock()
    mock.query.return_value = QueryResult(
        documents=["Some legal document text"],
        metadatas=[{"case_id": "CASE-001", "title": "Test Case"}],
        distances=[0.3],
    )
    return mock


def _make_mock_llm(response: str = "Here is my response"):
    """Create a mock LLM client."""
    mock = MagicMock()
    mock.chat.return_value = response
    return mock


def _make_mock_nav_store(matches: List[NavigationLinkEntry]):
    """Create a mock NavigationLinksStore that returns the given matches."""
    mock = MagicMock()
    mock.search.return_value = matches
    return mock


# ---------------------------------------------------------------------------
# Property 5: Navigation match triggers nav path, no match triggers ChromaDB fallback
# ---------------------------------------------------------------------------

# Feature: chatbot-navigation-links, Property 5: Navigation match triggers nav path, no match triggers ChromaDB fallback
# **Validates: Requirements 3.2, 3.4**
@given(
    message=_user_message_strategy(),
    history=_history_strategy(),
    nav_entries=st.lists(_nav_entry_strategy(), min_size=1, max_size=5),
)
@settings(max_examples=100)
def test_nav_match_triggers_nav_path_skips_chromadb(message, history, nav_entries):
    """When NavigationLinksStore returns non-empty matches, RAGEngine should
    produce a RAGResult with non-empty navigation_links and NOT query ChromaDB."""
    mock_chromadb = _make_mock_chromadb()
    mock_llm = _make_mock_llm()
    mock_nav_store = _make_mock_nav_store(nav_entries)

    engine = RAGEngine(mock_chromadb, mock_llm, max_context_chunks=5, navigation_store=mock_nav_store)
    result = engine.generate_response(message, history)

    # Navigation links should be non-empty
    assert len(result.navigation_links) > 0
    # ChromaDB should NOT have been queried
    mock_chromadb.query.assert_not_called()
    # LLM should still be called (to generate the response)
    mock_llm.chat.assert_called_once()


# Feature: chatbot-navigation-links, Property 5: Navigation match triggers nav path, no match triggers ChromaDB fallback
# **Validates: Requirements 3.2, 3.4**
@given(
    message=_user_message_strategy(),
    history=_history_strategy(),
)
@settings(max_examples=100)
def test_no_nav_match_triggers_chromadb_fallback(message, history):
    """When NavigationLinksStore returns empty matches, RAGEngine should
    query ChromaDB and produce a RAGResult with empty navigation_links."""
    mock_chromadb = _make_mock_chromadb()
    mock_llm = _make_mock_llm()
    mock_nav_store = _make_mock_nav_store([])  # No matches

    engine = RAGEngine(mock_chromadb, mock_llm, max_context_chunks=5, navigation_store=mock_nav_store)
    result = engine.generate_response(message, history)

    # Navigation links should be empty
    assert len(result.navigation_links) == 0
    # ChromaDB SHOULD have been queried
    mock_chromadb.query.assert_called_once()
    # LLM should still be called
    mock_llm.chat.assert_called_once()


# ---------------------------------------------------------------------------
# Property 6: Navigation prompt includes matched page names and routes
# ---------------------------------------------------------------------------

# Feature: chatbot-navigation-links, Property 6: Navigation prompt includes matched page names and routes
# **Validates: Requirements 3.3**
@given(
    message=_user_message_strategy(),
    history=_history_strategy(),
    nav_entries=st.lists(_nav_entry_strategy(), min_size=1, max_size=5),
)
@settings(max_examples=100)
def test_nav_prompt_includes_page_names_and_routes(message, history, nav_entries):
    """The prompt messages constructed by _build_nav_prompt should contain
    the page_name and route of every matched NavigationLinkEntry."""
    mock_chromadb = _make_mock_chromadb()
    mock_llm = _make_mock_llm()

    engine = RAGEngine(mock_chromadb, mock_llm, max_context_chunks=5)

    prompt_messages = engine._build_nav_prompt(message, history, nav_entries)

    # Concatenate all message contents for searching
    full_prompt_text = " ".join(m["content"] for m in prompt_messages)

    for entry in nav_entries:
        assert entry.page_name in full_prompt_text, (
            f"page_name '{entry.page_name}' not found in prompt"
        )
        assert entry.route in full_prompt_text, (
            f"route '{entry.route}' not found in prompt"
        )
