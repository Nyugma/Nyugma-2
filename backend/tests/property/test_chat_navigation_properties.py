"""
Property-based tests for chat route navigation response models.

Uses Hypothesis to verify correctness properties from the chatbot-navigation-links design.
"""

from typing import List

from hypothesis import given, settings
from hypothesis import strategies as st

from src.api.chat_routes import ChatResponse, NavigationLinkResponse, DocumentSourceResponse


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

def _non_empty_text(max_size: int = 30) -> st.SearchStrategy[str]:
    """Generate a non-empty, non-whitespace-only string."""
    return st.text(
        alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789 -_/"),
        min_size=1,
        max_size=max_size,
    ).filter(lambda s: s.strip())


def navigation_link_response_strategy() -> st.SearchStrategy[NavigationLinkResponse]:
    """Strategy that produces a NavigationLinkResponse with non-empty fields."""
    return st.builds(
        NavigationLinkResponse,
        page_name=_non_empty_text(),
        route=_non_empty_text(20).map(lambda s: "/" + s),
        description=_non_empty_text(60),
    )


def chat_response_with_nav_links_strategy() -> st.SearchStrategy[ChatResponse]:
    """Strategy that produces a ChatResponse containing navigation links."""
    return st.builds(
        ChatResponse,
        session_id=st.uuids().map(str),
        response=_non_empty_text(100),
        sources=st.just([]),
        navigation_links=st.lists(
            navigation_link_response_strategy(),
            min_size=1,
            max_size=5,
        ),
    )


# ---------------------------------------------------------------------------
# Property 7: Response navigation links contain required fields
# ---------------------------------------------------------------------------

# Feature: chatbot-navigation-links, Property 7: Response navigation links contain required fields
# **Validates: Requirements 4.1, 4.2**
@given(nav_link=navigation_link_response_strategy())
@settings(max_examples=100)
def test_navigation_link_response_has_required_non_empty_fields(nav_link):
    """Each NavigationLinkResponse must have non-empty page_name, route, and description."""
    assert isinstance(nav_link.page_name, str) and len(nav_link.page_name.strip()) > 0
    assert isinstance(nav_link.route, str) and len(nav_link.route.strip()) > 0
    assert isinstance(nav_link.description, str) and len(nav_link.description.strip()) > 0


# Feature: chatbot-navigation-links, Property 7: Response navigation links contain required fields
# **Validates: Requirements 4.1, 4.2**
@given(chat_resp=chat_response_with_nav_links_strategy())
@settings(max_examples=100)
def test_chat_response_preserves_navigation_link_fields(chat_resp):
    """A ChatResponse with navigation_links preserves all fields on each link."""
    assert len(chat_resp.navigation_links) > 0
    for link in chat_resp.navigation_links:
        assert isinstance(link, NavigationLinkResponse)
        assert link.page_name.strip() != ""
        assert link.route.strip() != ""
        assert link.description.strip() != ""
