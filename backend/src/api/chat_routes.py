"""
Chat API routes for the RAG chatbot.

Provides the POST /api/chat endpoint that orchestrates session management,
retrieval-augmented generation, and response formatting.
"""

import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from src.components.chromadb_client import ChromaDBClient
from src.components.llm_client import LLMClient
from src.components.rag_engine import RAGEngine
from src.components.session_manager import SessionManager

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level component references – set via ``init_chat_components()``
# when the router is registered in main.py (Task 7.2).
# ---------------------------------------------------------------------------
_rag_engine: Optional[RAGEngine] = None
_session_manager: Optional[SessionManager] = None

router = APIRouter(prefix="/api", tags=["chat"])


def init_chat_components(
    chromadb_client: ChromaDBClient,
    llm_client: LLMClient,
    session_manager: SessionManager,
    rag_engine: RAGEngine,
) -> None:
    """Inject runtime dependencies into the chat route module.

    Called once during application startup from ``main.py``.
    """
    global _rag_engine, _session_manager
    _rag_engine = rag_engine
    _session_manager = session_manager


# ---------------------------------------------------------------------------
# Pydantic request / response models
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    """Incoming chat message."""
    session_id: Optional[str] = None
    message: str = Field(..., min_length=1)


class DocumentSourceResponse(BaseModel):
    """A source document reference returned alongside a chat response."""
    case_id: str
    title: str
    snippet: str
    relevance_score: float


class ChatResponse(BaseModel):
    """Successful chat response."""
    session_id: str
    response: str
    sources: List[DocumentSourceResponse]


class ChatErrorResponse(BaseModel):
    """Standardised error envelope for chat errors."""
    error: bool = True
    message: str
    error_code: str
    timestamp: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _error_json(message: str, error_code: str, status_code: int) -> JSONResponse:
    """Build a ``JSONResponse`` matching the ``ChatErrorResponse`` schema."""
    return JSONResponse(
        status_code=status_code,
        content=ChatErrorResponse(
            message=message,
            error_code=error_code,
            timestamp=datetime.utcnow().isoformat(),
        ).model_dump(),
    )


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.post(
    "/chat",
    response_model=ChatResponse,
    responses={
        400: {"model": ChatErrorResponse, "description": "Bad request – empty message"},
        500: {"model": ChatErrorResponse, "description": "Internal server error"},
    },
    summary="Send a chat message",
    description="Send a message to the RAG chatbot and receive an AI-generated response with source references.",
)
async def chat(request: ChatRequest) -> ChatResponse:
    """Process a chat message through the RAG pipeline.

    Flow:
    1. Validate that the message is not whitespace-only.
    2. Load or create a session via ``SessionManager``.
    3. Call ``RAGEngine.generate_response()`` with the message and history.
    4. Persist the updated session.
    5. Return the response with sources.

    Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6
    """

    # --- 1. Reject whitespace-only messages --------------------------------
    if not request.message.strip():
        return _error_json(
            message="Message must not be empty or whitespace-only.",
            error_code="EMPTY_MESSAGE",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    try:
        # --- 2. Load or create session -------------------------------------
        session = _session_manager.load_or_create(request.session_id)
        history = _session_manager.get_recent_messages(session)

        # --- 3. Generate RAG response --------------------------------------
        rag_result = _rag_engine.generate_response(request.message, history)

        # --- 4. Persist session with new messages --------------------------
        _session_manager.append_messages(
            session, request.message, rag_result.response
        )
        _session_manager.save(session)

        # --- 5. Build and return response ----------------------------------
        sources = [
            DocumentSourceResponse(
                case_id=src.case_id,
                title=src.title,
                snippet=src.snippet,
                relevance_score=src.relevance_score,
            )
            for src in rag_result.sources
        ]

        return ChatResponse(
            session_id=session.session_id,
            response=rag_result.response,
            sources=sources,
        )

    except Exception:
        logger.exception("Internal error while processing chat request")
        return _error_json(
            message="An internal server error occurred. Please try again later.",
            error_code="INTERNAL_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
