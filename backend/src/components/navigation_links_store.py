"""
Navigation links store for the Nyugma Legal Case Similarity chatbot.

Loads, validates, and searches navigation link entries from a JSON data file.
"""

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)

REQUIRED_FIELDS = {"id", "page_name", "route", "description", "keywords", "roles"}


@dataclass
class NavigationLinkEntry:
    """A single navigation link record."""

    id: str
    page_name: str
    route: str
    description: str
    keywords: List[str]
    roles: List[str]


class NavigationLinksStore:
    """Loads, validates, caches, and searches navigation link entries.

    The store reads a JSON file at startup, validates each entry, skips
    invalid or duplicate entries with logged warnings, and provides
    keyword-based search sorted by relevance.
    """

    def __init__(self, file_path: str = "data/navigation_links.json"):
        self._entries: List[NavigationLinkEntry] = []
        self._load_and_validate(file_path)

    def _load_and_validate(self, file_path: str) -> None:
        """Load JSON, validate each entry, skip invalid ones, reject duplicate IDs."""
        path = Path(file_path)
        if not path.exists():
            logger.warning("Navigation links file not found: %s", file_path)
            return

        try:
            raw_text = path.read_text(encoding="utf-8")
        except Exception:
            logger.warning("Unable to read navigation links file: %s", file_path, exc_info=True)
            return

        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError:
            logger.warning("Navigation links file is not valid JSON: %s", file_path)
            return

        raw_entries = data.get("navigation_links", [])
        if not isinstance(raw_entries, list):
            logger.warning("Expected 'navigation_links' to be a list in %s", file_path)
            return

        seen_ids: set = set()
        for entry in raw_entries:
            if not isinstance(entry, dict):
                logger.warning("Skipping non-dict navigation link entry")
                continue

            # Required fields check
            missing = REQUIRED_FIELDS - entry.keys()
            if missing:
                entry_id = entry.get("id", "<unknown>")
                logger.warning("Skipping entry '%s': missing fields %s", entry_id, missing)
                continue

            # Route must start with /
            if not isinstance(entry["route"], str) or not entry["route"].startswith("/"):
                logger.warning("Skipping entry '%s': route must start with '/'", entry.get("id"))
                continue

            # Keywords must be a non-empty list of strings
            kw = entry["keywords"]
            if (
                not isinstance(kw, list)
                or len(kw) == 0
                or not all(isinstance(k, str) for k in kw)
            ):
                logger.warning("Skipping entry '%s': keywords must be a non-empty list of strings", entry.get("id"))
                continue

            # Duplicate ID rejection
            entry_id = entry["id"]
            if entry_id in seen_ids:
                logger.warning("Skipping duplicate entry id '%s'", entry_id)
                continue
            seen_ids.add(entry_id)

            self._entries.append(
                NavigationLinkEntry(
                    id=entry_id,
                    page_name=entry["page_name"],
                    route=entry["route"],
                    description=entry["description"],
                    keywords=entry["keywords"],
                    roles=entry["roles"],
                )
            )

        logger.info("Loaded %d navigation link entries", len(self._entries))

    def search(self, query: str) -> List[NavigationLinkEntry]:
        """Return entries whose keywords match the query, sorted by relevance.

        Matching logic:
        - Normalize the query to lowercase
        - For each entry, count how many of its keywords appear as a substring
          in the query OR how many query words appear in any keyword
        - Score = total number of keyword matches
        - Return matched entries sorted by score descending
        """
        if not query or not query.strip():
            return []

        normalized_query = query.lower().strip()
        query_words = normalized_query.split()

        scored: List[tuple] = []
        for entry in self._entries:
            score = 0
            for keyword in entry.keywords:
                kw_lower = keyword.lower()
                # keyword appears as substring in query
                if kw_lower in normalized_query:
                    score += 1
                    continue
                # any query word appears in the keyword
                for word in query_words:
                    if word in kw_lower:
                        score += 1
                        break
            if score > 0:
                scored.append((score, entry))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [entry for _, entry in scored]

    @property
    def entries(self) -> List[NavigationLinkEntry]:
        """All valid loaded entries."""
        return list(self._entries)
