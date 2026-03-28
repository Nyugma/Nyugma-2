"""
ChromaDB client wrapper for querying the legal cases vector store.
"""

import logging
from dataclasses import dataclass, field
from typing import List

import chromadb

from src.config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class QueryResult:
    """Result from a ChromaDB query."""
    documents: List[str] = field(default_factory=list)
    metadatas: List[dict] = field(default_factory=list)
    distances: List[float] = field(default_factory=list)


class ChromaDBClient:
    """Wrapper around ChromaDB for querying the legal_cases collection."""

    def __init__(self, persist_directory: str = None):
        self.persist_directory = persist_directory or str(settings.CHROMADB_DIR)
        try:
            self.client = chromadb.PersistentClient(path=self.persist_directory)
            self.collection = self.client.get_or_create_collection("legal_cases")
            logger.info("ChromaDB client connected at %s", self.persist_directory)
        except Exception:
            logger.exception("Failed to connect to ChromaDB at %s", self.persist_directory)
            raise

    def query(self, query_text: str, n_results: int = 5) -> QueryResult:
        """Query the legal_cases collection by semantic similarity.

        Args:
            query_text: The text to search for.
            n_results: Maximum number of results to return.

        Returns:
            A QueryResult with documents, metadatas, and distances.
        """
        try:
            results = self.collection.query(
                query_texts=[query_text],
                n_results=n_results,
            )
            return QueryResult(
                documents=results["documents"][0] if results["documents"] else [],
                metadatas=results["metadatas"][0] if results["metadatas"] else [],
                distances=results["distances"][0] if results["distances"] else [],
            )
        except Exception:
            logger.exception("ChromaDB query failed for text: %s", query_text[:100])
            raise
