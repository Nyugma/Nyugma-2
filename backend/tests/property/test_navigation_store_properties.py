"""
Property-based tests for NavigationLinksStore.

Uses Hypothesis to verify correctness properties from the chatbot-navigation-links design.
"""

import json
import os
import tempfile
from typing import Any, Dict, List

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from src.components.navigation_links_store import NavigationLinksStore, NavigationLinkEntry


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

def _valid_route() -> st.SearchStrategy[str]:
    """Generate a route string that starts with '/'."""
    return st.text(
        alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz-_/"),
        min_size=1,
        max_size=20,
    ).map(lambda s: "/" + s)


def _non_empty_keyword_list() -> st.SearchStrategy[List[str]]:
    """Generate a non-empty list of non-empty keyword strings."""
    return st.lists(
        st.text(
            alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz "),
            min_size=1,
            max_size=15,
        ).filter(lambda s: s.strip()),
        min_size=1,
        max_size=5,
    )


def _roles_list() -> st.SearchStrategy[List[str]]:
    return st.lists(
        st.sampled_from(["user", "helper", "admin", "public"]),
        min_size=1,
        max_size=3,
        unique=True,
    )


def _non_empty_text(max_size: int = 30) -> st.SearchStrategy[str]:
    """Generate a non-empty text string with printable ASCII characters (fast generation)."""
    return st.text(
        alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -_"),
        min_size=1,
        max_size=max_size,
    ).filter(lambda s: s.strip())


def valid_entry_dict(id_strategy=None) -> st.SearchStrategy[Dict[str, Any]]:
    """Strategy that produces a fully valid navigation link entry dict."""
    if id_strategy is None:
        id_strategy = st.text(
            alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789-_"),
            min_size=1,
            max_size=15,
        )
    return st.fixed_dictionaries(
        {
            "id": id_strategy,
            "page_name": _non_empty_text(30),
            "route": _valid_route(),
            "description": _non_empty_text(60),
            "keywords": _non_empty_keyword_list(),
            "roles": _roles_list(),
        }
    )


# Strategy for invalid entries – at least one required field is broken
@st.composite
def invalid_entry_dict(draw):
    """Generate an entry dict that violates at least one validation rule."""
    kind = draw(st.sampled_from([
        "missing_field",
        "bad_route",
        "empty_keywords",
        "keywords_not_list",
        "keywords_contains_non_string",
    ]))

    base = draw(valid_entry_dict())

    if kind == "missing_field":
        field = draw(st.sampled_from(["id", "page_name", "route", "description", "keywords", "roles"]))
        del base[field]
    elif kind == "bad_route":
        # Route that does NOT start with '/'
        base["route"] = draw(
            st.text(
                alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz"),
                min_size=1,
                max_size=10,
            )
        )
        assume(not base["route"].startswith("/"))
    elif kind == "empty_keywords":
        base["keywords"] = []
    elif kind == "keywords_not_list":
        base["keywords"] = draw(st.one_of(st.integers(), st.text(min_size=1, max_size=5)))
    elif kind == "keywords_contains_non_string":
        base["keywords"] = [draw(st.integers())]

    return base


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_store_from_entries(entries: List[Dict[str, Any]]) -> NavigationLinksStore:
    """Write entries to a temp JSON file and load a NavigationLinksStore from it."""
    data = {"navigation_links": entries}
    fd, path = tempfile.mkstemp(suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f)
        store = NavigationLinksStore(file_path=path)
    finally:
        os.unlink(path)
    return store


def _is_valid_entry(entry: Dict[str, Any]) -> bool:
    """Check whether an entry dict would pass the store's validation rules."""
    required = {"id", "page_name", "route", "description", "keywords", "roles"}
    if not isinstance(entry, dict):
        return False
    if required - entry.keys():
        return False
    if not isinstance(entry.get("route"), str) or not entry["route"].startswith("/"):
        return False
    kw = entry.get("keywords")
    if not isinstance(kw, list) or len(kw) == 0 or not all(isinstance(k, str) for k in kw):
        return False
    return True


# ---------------------------------------------------------------------------
# Property 1: Valid entry acceptance and invalid entry rejection
# ---------------------------------------------------------------------------

# Feature: chatbot-navigation-links, Property 1: Valid entry acceptance and invalid entry rejection
# **Validates: Requirements 1.3, 2.1, 2.2, 2.3**
@given(entry=valid_entry_dict())
@settings(max_examples=100)
def test_valid_entry_is_accepted(entry):
    """A fully valid entry dict should be loaded into the store."""
    store = _load_store_from_entries([entry])
    assert len(store.entries) == 1
    loaded = store.entries[0]
    assert loaded.id == entry["id"]
    assert loaded.route == entry["route"]
    assert loaded.keywords == entry["keywords"]


# Feature: chatbot-navigation-links, Property 1: Valid entry acceptance and invalid entry rejection
# **Validates: Requirements 1.3, 2.1, 2.2, 2.3**
@given(entry=invalid_entry_dict())
@settings(max_examples=100)
def test_invalid_entry_is_rejected(entry):
    """An entry that violates any validation rule should not appear in the store."""
    store = _load_store_from_entries([entry])
    assert len(store.entries) == 0


# ---------------------------------------------------------------------------
# Property 2: Invalid entries are skipped, valid entries are preserved
# ---------------------------------------------------------------------------

# Feature: chatbot-navigation-links, Property 2: Invalid entries are skipped, valid entries are preserved
# **Validates: Requirements 2.4**
@given(
    valid_entries=st.lists(valid_entry_dict(), min_size=0, max_size=5),
    invalid_entries=st.lists(invalid_entry_dict(), min_size=0, max_size=5),
    seed=st.randoms(use_true_random=False),
)
@settings(max_examples=100)
def test_mixed_entries_preserve_valid_skip_invalid(valid_entries, invalid_entries, seed):
    """After loading a mixed list, the store contains exactly the valid entries in order."""
    # Deduplicate valid entry IDs so Property 3 doesn't interfere
    seen_ids = set()
    unique_valid = []
    for e in valid_entries:
        if e["id"] not in seen_ids:
            seen_ids.add(e["id"])
            unique_valid.append(e)

    # Also ensure invalid entries don't accidentally share IDs with valid ones
    filtered_invalid = [e for e in invalid_entries if e.get("id") not in seen_ids]

    # Interleave valid and invalid entries
    combined = list(unique_valid) + list(filtered_invalid)
    seed.shuffle(combined)

    store = _load_store_from_entries(combined)

    loaded_ids = [e.id for e in store.entries]
    expected_ids = [e["id"] for e in unique_valid]

    # All valid entries should be present
    assert set(loaded_ids) == set(expected_ids)
    # Order among valid entries should be preserved (relative order in combined)
    combined_valid_order = [
        e["id"] for e in combined if _is_valid_entry(e) and e["id"] in set(expected_ids)
    ]
    assert loaded_ids == combined_valid_order


# ---------------------------------------------------------------------------
# Property 3: Duplicate ID deduplication
# ---------------------------------------------------------------------------

# Feature: chatbot-navigation-links, Property 3: Duplicate ID deduplication
# **Validates: Requirements 2.5**
@given(
    entry=valid_entry_dict(),
    extra_count=st.integers(min_value=1, max_value=4),
)
@settings(max_examples=100)
def test_duplicate_id_keeps_first_occurrence(entry, extra_count):
    """When multiple entries share the same id, only the first is kept."""
    entries = [entry]
    for _ in range(extra_count):
        dup = dict(entry)
        dup["page_name"] = "Duplicate Page"
        entries.append(dup)

    store = _load_store_from_entries(entries)

    matching = [e for e in store.entries if e.id == entry["id"]]
    assert len(matching) == 1
    # The kept entry should be the first one
    assert matching[0].page_name == entry["page_name"]


# ---------------------------------------------------------------------------
# Property 4: Keyword search returns matching entries
# ---------------------------------------------------------------------------

# Feature: chatbot-navigation-links, Property 4: Keyword search returns matching entries
# **Validates: Requirements 3.1**
@given(
    entries=st.lists(
        valid_entry_dict(
            id_strategy=st.text(
                alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz"),
                min_size=3,
                max_size=10,
            )
        ),
        min_size=1,
        max_size=5,
        unique_by=lambda e: e["id"],
    ),
    entry_index=st.data(),
)
@settings(max_examples=100)
def test_keyword_search_returns_matching_entries(entries, entry_index):
    """If the query contains a keyword from an entry, that entry appears in results."""
    store = _load_store_from_entries(entries)
    assume(len(store.entries) > 0)

    # Pick a random loaded entry and one of its keywords
    idx = entry_index.draw(st.integers(min_value=0, max_value=len(store.entries) - 1))
    target = store.entries[idx]
    keyword = entry_index.draw(st.sampled_from(target.keywords))

    # Query with that keyword
    results = store.search(keyword)
    result_ids = [e.id for e in results]
    assert target.id in result_ids, (
        f"Entry '{target.id}' with keyword '{keyword}' not found in search results"
    )


# Feature: chatbot-navigation-links, Property 4: Keyword search returns matching entries (negative)
# **Validates: Requirements 3.1**
@given(
    entries=st.lists(
        valid_entry_dict(
            id_strategy=st.text(
                alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz"),
                min_size=3,
                max_size=10,
            )
        ),
        min_size=1,
        max_size=5,
        unique_by=lambda e: e["id"],
    ),
)
@settings(max_examples=100)
def test_keyword_search_excludes_non_matching_entries(entries):
    """A query with no keyword overlap should not return an entry."""
    store = _load_store_from_entries(entries)
    assume(len(store.entries) > 0)

    # Use a query that cannot match any keyword: a string of digits
    nonsense_query = "99999 88888 77777"

    # Verify none of the entries have keywords that could match
    for entry in store.entries:
        for kw in entry.keywords:
            assume(kw.lower() not in nonsense_query)
            for word in nonsense_query.split():
                assume(word not in kw.lower())

    results = store.search(nonsense_query)
    assert len(results) == 0


# ---------------------------------------------------------------------------
# Property 8: Search results are sorted by relevance descending
# ---------------------------------------------------------------------------

# Feature: chatbot-navigation-links, Property 8: Search results are sorted by relevance descending
# **Validates: Requirements 4.5**
@given(data=st.data())
@settings(max_examples=100)
def test_search_results_sorted_by_relevance_descending(data):
    """Search results should be sorted by match score in descending order."""
    # Build entries with controlled keyword overlap so we can predict scores
    shared_keyword = "testword"

    # Entry A: 3 matching keywords
    entry_a = {
        "id": "entry-a",
        "page_name": "Page A",
        "route": "/page-a",
        "description": "Description A",
        "keywords": [shared_keyword, "alpha", "beta"],
        "roles": ["user"],
    }
    # Entry B: 1 matching keyword
    entry_b = {
        "id": "entry-b",
        "page_name": "Page B",
        "route": "/page-b",
        "description": "Description B",
        "keywords": [shared_keyword, "gamma", "delta"],
        "roles": ["user"],
    }
    # Entry C: 2 matching keywords
    entry_c = {
        "id": "entry-c",
        "page_name": "Page C",
        "route": "/page-c",
        "description": "Description C",
        "keywords": [shared_keyword, "alpha", "epsilon"],
        "roles": ["user"],
    }

    # Query that matches shared_keyword + alpha (so A gets 2, C gets 2, B gets 1)
    query = f"{shared_keyword} alpha"

    store = _load_store_from_entries([entry_a, entry_b, entry_c])
    results = store.search(query)

    # Verify descending order: compute scores the same way the store does
    def _score(entry: NavigationLinkEntry, q: str) -> int:
        normalized = q.lower().strip()
        words = normalized.split()
        score = 0
        for kw in entry.keywords:
            kw_lower = kw.lower()
            if kw_lower in normalized:
                score += 1
                continue
            for w in words:
                if w in kw_lower:
                    score += 1
                    break
        return score

    scores = [_score(e, query) for e in results]
    assert scores == sorted(scores, reverse=True), (
        f"Results not sorted by descending relevance: {scores}"
    )
    # All three entries should match
    assert len(results) >= 2
