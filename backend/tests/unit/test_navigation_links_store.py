"""
Unit tests for NavigationLinksStore.

Requirements: 1.1, 1.2, 1.5, 2.1, 2.2, 2.3, 2.4, 2.5
"""

import json
import logging
from pathlib import Path

import pytest

from src.components.navigation_links_store import NavigationLinksStore, NavigationLinkEntry


def _make_valid_entry(**overrides):
    """Return a valid navigation link entry dict with optional overrides."""
    base = {
        "id": "test-page",
        "page_name": "Test Page",
        "route": "/test",
        "description": "A test page.",
        "keywords": ["test", "example"],
        "roles": ["user"],
    }
    base.update(overrides)
    return base


def _write_nav_json(path: Path, entries: list):
    """Write a navigation_links.json file with the given entries."""
    path.write_text(json.dumps({"navigation_links": entries}), encoding="utf-8")


# ---------------------------------------------------------------------------
# Loading: valid JSON
# ---------------------------------------------------------------------------

class TestLoadValidJSON:
    def test_loads_entries_from_valid_file(self, tmp_path):
        f = tmp_path / "nav.json"
        _write_nav_json(f, [_make_valid_entry()])
        store = NavigationLinksStore(file_path=str(f))

        assert len(store.entries) == 1
        assert store.entries[0].id == "test-page"
        assert store.entries[0].page_name == "Test Page"
        assert store.entries[0].route == "/test"

    def test_loads_multiple_entries(self, tmp_path):
        f = tmp_path / "nav.json"
        entries = [
            _make_valid_entry(id="a", page_name="Page A", route="/a"),
            _make_valid_entry(id="b", page_name="Page B", route="/b"),
        ]
        _write_nav_json(f, entries)
        store = NavigationLinksStore(file_path=str(f))

        assert len(store.entries) == 2
        assert [e.id for e in store.entries] == ["a", "b"]


# ---------------------------------------------------------------------------
# Loading: missing file
# ---------------------------------------------------------------------------

class TestMissingFile:
    def test_missing_file_results_in_empty_store(self, tmp_path, caplog):
        missing = tmp_path / "does_not_exist.json"
        with caplog.at_level(logging.WARNING):
            store = NavigationLinksStore(file_path=str(missing))

        assert store.entries == []
        assert "not found" in caplog.text.lower()


# ---------------------------------------------------------------------------
# Loading: malformed JSON
# ---------------------------------------------------------------------------

class TestMalformedJSON:
    def test_malformed_json_results_in_empty_store(self, tmp_path, caplog):
        f = tmp_path / "bad.json"
        f.write_text("{not valid json!!!", encoding="utf-8")
        with caplog.at_level(logging.WARNING):
            store = NavigationLinksStore(file_path=str(f))

        assert store.entries == []
        assert "not valid json" in caplog.text.lower()


# ---------------------------------------------------------------------------
# Real data file: all 9 platform pages present
# ---------------------------------------------------------------------------

EXPECTED_PAGE_IDS = {
    "home",
    "auth",
    "dashboard",
    "helper-dashboard",
    "search",
    "inquiry",
    "connections",
    "messages",
    "admin",
}

EXPECTED_ROUTES = {
    "/",
    "/auth",
    "/dashboard",
    "/helper-dashboard",
    "/search",
    "/inquiry",
    "/connections",
    "/messages",
    "/admin",
}


class TestRealDataFile:
    """Load the actual navigation_links.json and verify completeness."""

    @pytest.fixture()
    def store(self):
        return NavigationLinksStore(file_path="data/navigation_links.json")

    def test_contains_all_9_pages(self, store):
        assert len(store.entries) == 9

    def test_all_expected_ids_present(self, store):
        ids = {e.id for e in store.entries}
        assert ids == EXPECTED_PAGE_IDS

    def test_all_expected_routes_present(self, store):
        routes = {e.route for e in store.entries}
        assert routes == EXPECTED_ROUTES

    def test_every_entry_has_keywords(self, store):
        for entry in store.entries:
            assert isinstance(entry.keywords, list)
            assert len(entry.keywords) > 0

    def test_every_entry_has_roles(self, store):
        for entry in store.entries:
            assert isinstance(entry.roles, list)
            assert len(entry.roles) > 0


# ---------------------------------------------------------------------------
# Keyword search: known queries
# ---------------------------------------------------------------------------

class TestKeywordSearchKnown:
    """Search with queries that should match specific pages."""

    @pytest.fixture()
    def store(self):
        return NavigationLinksStore(file_path="data/navigation_links.json")

    def test_login_returns_auth_page(self, store):
        results = store.search("login")
        ids = [r.id for r in results]
        assert "auth" in ids

    def test_upload_document_returns_dashboard(self, store):
        results = store.search("upload document")
        ids = [r.id for r in results]
        assert "dashboard" in ids

    def test_send_message_returns_messages_page(self, store):
        results = store.search("send message")
        ids = [r.id for r in results]
        assert "messages" in ids

    def test_manage_users_returns_admin_page(self, store):
        results = store.search("manage users")
        ids = [r.id for r in results]
        assert "admin" in ids

    def test_find_similar_cases_returns_search_page(self, store):
        results = store.search("find similar cases")
        ids = [r.id for r in results]
        assert "search" in ids

    def test_submit_inquiry_returns_inquiry_page(self, store):
        results = store.search("submit inquiry")
        ids = [r.id for r in results]
        assert "inquiry" in ids


# ---------------------------------------------------------------------------
# Keyword search: unrelated query
# ---------------------------------------------------------------------------

class TestKeywordSearchUnrelated:
    @pytest.fixture()
    def store(self):
        return NavigationLinksStore(file_path="data/navigation_links.json")

    def test_unrelated_query_returns_empty(self, store):
        results = store.search("quantum physics black hole")
        assert results == []

    def test_empty_query_returns_empty(self, store):
        assert store.search("") == []

    def test_whitespace_query_returns_empty(self, store):
        assert store.search("   ") == []
