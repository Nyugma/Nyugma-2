"""
Components package for Legal Case Similarity Application

This package contains the core processing components:
- PDFProcessor: PDF text extraction and validation
- TextPreprocessor: Text normalization and preprocessing
- LegalVectorizer: TF-IDF vectorization using legal vocabulary
- SimilaritySearchEngine: Cosine similarity search and K-NN retrieval
- CaseRepository: Case document and vector storage management
- ChromaDBClient: ChromaDB vector store client for RAG retrieval
- LLMClient: OpenAI LLM client for chat completions
- SessionManager: JSON file-based chat session persistence
- ChatSession: Dataclass representing a chat session
- RAGEngine: Retrieval-augmented generation engine
- RAGResult: Result dataclass from RAG engine
- DocumentSource: Source document reference dataclass
"""

from .pdf_processor import PDFProcessor
from .text_preprocessor import TextPreprocessor
from .legal_vectorizer import LegalVectorizer
from .similarity_search_engine import SimilaritySearchEngine
from .case_repository import CaseRepository
from .chromadb_client import ChromaDBClient, QueryResult
from .llm_client import LLMClient
from .session_manager import SessionManager, ChatSession
from .rag_engine import RAGEngine, RAGResult, DocumentSource

__all__ = ['PDFProcessor', 'TextPreprocessor', 'LegalVectorizer', 'SimilaritySearchEngine', 'CaseRepository', 'ChromaDBClient', 'QueryResult', 'LLMClient', 'SessionManager', 'ChatSession', 'RAGEngine', 'RAGResult', 'DocumentSource']