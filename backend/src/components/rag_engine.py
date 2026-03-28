"""
RAG Engine for the Nyugma Legal Case Similarity chatbot.

Orchestrates retrieval from ChromaDB and response generation via the LLM client.
"""

import logging
from dataclasses import dataclass, field
from typing import List

from src.config.settings import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a legal research assistant for the Nyugma Legal Case Similarity platform. "
    "Answer questions based on the provided legal case context. If the context does not "
    "contain relevant information, say so clearly. Be concise and cite case references "
    "when available."
)

NO_RESULTS_ADDENDUM = (
    "\n\nNo specific case documents were found in the knowledge base for this query. "
    "Please respond based on your general legal knowledge and clearly indicate that "
    "no specific case data was found."
)

FALLBACK_RESPONSE = (
    "I'm sorry, the legal knowledge base is temporarily unavailable. "
    "Please try again later."
)


@dataclass
class DocumentSource:
    """A source document reference returned alongside a RAG response."""

    case_id: str
    title: str
    snippet: str
    relevance_score: float


@dataclass
class RAGResult:
    """Result from the RAG engine containing the LLM response and source documents."""

    response: str
    sources: List[DocumentSource] = field(default_factory=list)


class RAGEngine:
    """Orchestrates retrieval-augmented generation for legal case queries.

    Queries ChromaDB for relevant document chunks, builds a prompt with
    system instructions, context, conversation history, and the user message,
    then calls the LLM to generate a response.
    """

    def __init__(self, chromadb_client, llm_client, max_context_chunks: int = None):
        self.chromadb_client = chromadb_client
        self.llm_client = llm_client
        self.max_context_chunks = (
            max_context_chunks if max_context_chunks is not None else settings.MAX_CONTEXT_CHUNKS
        )

    def generate_response(self, message: str, history: List[dict]) -> RAGResult:
        """Generate a RAG response for the given user message.

        Args:
            message: The current user message.
            history: Previous conversation messages as a list of
                     ``{"role": ..., "content": ...}`` dicts.

        Returns:
            A RAGResult with the LLM response text and source documents.
        """
        # 1. Retrieve relevant chunks from ChromaDB
        try:
            query_result = self.chromadb_client.query(
                message, n_results=self.max_context_chunks
            )
        except Exception:
            logger.exception("ChromaDB query failed, returning fallback response")
            return RAGResult(response=FALLBACK_RESPONSE, sources=[])

        # 2. Extract sources from query metadata
        sources = self._extract_sources(query_result)

        # 3. Build prompt messages
        prompt_messages = self._build_prompt(message, history, query_result)

        # 4. Call LLM
        try:
            llm_response = self.llm_client.chat(prompt_messages)
        except Exception:
            logger.exception("LLM call failed during RAG generation")
            raise

        return RAGResult(response=llm_response, sources=sources)

    def _build_prompt(self, message: str, history: List[dict], query_result) -> List[dict]:
        """Construct the list of messages to send to the LLM.

        The prompt is structured as:
        1. System instruction (with optional no-results addendum)
        2. Context from retrieved chunks (as a single system message)
        3. Conversation history
        4. Current user message
        """
        messages: List[dict] = []

        # System prompt
        system_content = SYSTEM_PROMPT
        has_results = bool(query_result.documents)
        if not has_results:
            system_content += NO_RESULTS_ADDENDUM
        messages.append({"role": "system", "content": system_content})

        # Context from retrieved chunks
        if has_results:
            context_text = self._format_context(query_result)
            messages.append({"role": "system", "content": context_text})

        # Conversation history
        for msg in history:
            messages.append({"role": msg["role"], "content": msg["content"]})

        # Current user message
        messages.append({"role": "user", "content": message})

        return messages

    @staticmethod
    def _format_context(query_result) -> str:
        """Format retrieved document chunks into a context string."""
        parts = ["Relevant legal case context:"]
        for i, (doc, meta) in enumerate(
            zip(query_result.documents, query_result.metadatas), start=1
        ):
            case_id = meta.get("case_id", "unknown")
            title = meta.get("title", "Untitled")
            parts.append(f"\n[{i}] Case {case_id} - {title}:\n{doc}")
        return "\n".join(parts)

    @staticmethod
    def _extract_sources(query_result) -> List[DocumentSource]:
        """Build DocumentSource list from ChromaDB query results."""
        sources: List[DocumentSource] = []
        for doc, meta, distance in zip(
            query_result.documents,
            query_result.metadatas,
            query_result.distances,
        ):
            # ChromaDB distances are L2; convert to a 0-1 relevance score
            relevance = max(0.0, 1.0 - distance)
            sources.append(
                DocumentSource(
                    case_id=meta.get("case_id", "unknown"),
                    title=meta.get("title", "Untitled"),
                    snippet=doc[:200] if doc else "",
                    relevance_score=round(relevance, 4),
                )
            )
        return sources
