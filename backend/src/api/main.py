"""
FastAPI application for Legal Case Similarity Web Application

This module provides the main FastAPI application with endpoints for:
- PDF file upload and similarity search
- Case retrieval and metadata access
- System health monitoring
"""

import os
import tempfile
import logging
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from fastapi import FastAPI, File, UploadFile, HTTPException, status, Request, Depends
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ValidationError
import traceback

from src.config.settings import settings
from src.components.pdf_processor import PDFProcessor
from src.components.text_preprocessor import TextPreprocessor
from src.components.legal_vectorizer import LegalVectorizer
from src.components.similarity_search_engine import SimilaritySearchEngine
from src.components.case_repository import CaseRepository
from src.components.performance_monitor import get_performance_monitor
from src.components.inquiry_repository import InquiryRepository
from src.models.legal_vocabulary import LegalVocabulary
from src.models.search_result import SearchResult
from src.models.inquiry import InquiryCreate, InquiryResponse, InquiryListResponse
from src.api.auth_routes import router as auth_router, get_current_user
from src.models.user import User
from src.config.database import get_db
from sqlalchemy.orm import Session

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Legal Case Similarity API",
    description="API for finding similar legal cases using document similarity analysis",
    version="1.0.0"
)

# Configure CORS middleware with environment variable support
# Get allowed origins from environment variable, default to "*" for development
cors_origins_env = os.getenv("CORS_ORIGINS", "*")
allowed_origins = [origin.strip() for origin in cors_origins_env.split(",")] if cors_origins_env != "*" else ["*"]

# Log CORS configuration on startup
logger.info(f"CORS configuration: allowed_origins={allowed_origins}")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)

# Initialize components
pdf_processor = PDFProcessor()
text_preprocessor = TextPreprocessor(enable_lemmatization=True)
case_repository = CaseRepository()
performance_monitor = get_performance_monitor()
inquiry_repository = InquiryRepository()

# Initialize vectorizer with legal vocabulary
legal_vocabulary = LegalVocabulary()
vectorizer = LegalVectorizer(vocabulary=legal_vocabulary)

# Load pre-trained vectorizer model if available
vectorizer_model_path = Path("data/vectorizer_model.pkl")
if vectorizer_model_path.exists():
    try:
        vectorizer.load_model(vectorizer_model_path)
        logger.info("Loaded pre-trained vectorizer model")
    except Exception as e:
        logger.warning(f"Failed to load vectorizer model: {e}")

# Initialize similarity search engine
case_vectors = case_repository.load_case_vectors()
case_metadata = case_repository.load_case_metadata()

if case_vectors is not None and case_metadata:
    similarity_engine = SimilaritySearchEngine(case_vectors, case_metadata)
    logger.info(f"Initialized similarity engine with {len(case_metadata)} cases")
else:
    similarity_engine = None
    logger.warning("No case data available - similarity search will be limited")

# Initialize chat/RAG components
from src.api.chat_routes import router as chat_router, init_chat_components
from src.components.chromadb_client import ChromaDBClient
from src.components.llm_client import LLMClient
from src.components.session_manager import SessionManager
from src.components.rag_engine import RAGEngine
from src.components.navigation_links_store import NavigationLinksStore

try:
    chat_chromadb_client = ChromaDBClient()
    chat_llm_client = LLMClient()
    chat_session_manager = SessionManager()
    nav_store = NavigationLinksStore(file_path=str(settings.NAVIGATION_LINKS_PATH))
    chat_rag_engine = RAGEngine(chat_chromadb_client, chat_llm_client, navigation_store=nav_store)
    init_chat_components(chat_chromadb_client, chat_llm_client, chat_session_manager, chat_rag_engine)
    app.include_router(chat_router)
    logger.info("Chat/RAG components initialized successfully")
except Exception as e:
    logger.warning(f"Failed to initialize chat components: {e}")
    # Still include the router so the endpoint exists but returns errors
    app.include_router(chat_router)


# Pydantic models for request/response validation
class SimilarCase(BaseModel):
    """Model for similar case in search results."""
    case_id: str = Field(..., description="Unique case identifier")
    title: str = Field(..., description="Case title")
    date: str = Field(..., description="Case date")
    similarity_score: float = Field(..., ge=0.0, le=1.0, description="Similarity score (0-1)")
    snippet: str = Field(..., description="Brief text excerpt")
    download_url: str = Field(..., description="URL to download case file")


class UploadResponse(BaseModel):
    """Response model for file upload endpoint."""
    results: List[SimilarCase] = Field(..., description="List of similar cases")
    processing_time: float = Field(..., description="Processing time in seconds")
    query_id: str = Field(..., description="Unique query identifier")
    total_cases_searched: int = Field(..., description="Total number of cases in repository")


class ErrorResponse(BaseModel):
    """Standard error response model."""
    error: bool = Field(True, description="Error flag")
    message: str = Field(..., description="Error message")
    error_code: str = Field(..., description="Error code")
    timestamp: str = Field(..., description="Error timestamp")


class APIInfo(BaseModel):
    """Model for root endpoint API information."""
    name: str = Field(..., description="API name")
    version: str = Field(..., description="API version")
    description: str = Field(..., description="API description")
    endpoints: dict = Field(..., description="Available endpoints with their HTTP methods and descriptions")
    documentation: str = Field(..., description="Interactive API documentation URL")
    frontend_url: str = Field(..., description="Frontend application URL")


# Configuration constants
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_CONTENT_TYPES = ["application/pdf"]
DEFAULT_RESULTS_COUNT = 10


# Utility functions for error handling
def create_error_response(
    message: str,
    error_code: str,
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
) -> HTTPException:
    """
    Create a standardized HTTPException with error response format.
    
    Args:
        message: Error message
        error_code: Error code identifier
        status_code: HTTP status code
        
    Returns:
        HTTPException with standardized error detail
        
    Requirements: 7.3, 7.4, 7.5 - Standardized error responses
    """
    error_detail = {
        "error": True,
        "message": message,
        "error_code": error_code,
        "timestamp": datetime.now().isoformat()
    }
    
    return HTTPException(status_code=status_code, detail=error_detail)


def validate_file_upload(file: UploadFile) -> None:
    """
    Validate uploaded file meets requirements.
    
    Args:
        file: Uploaded file to validate
        
    Raises:
        HTTPException: If file validation fails
        
    Requirements: 7.4 - Request validation
    """
    # Validate file size
    if file.size and file.size > MAX_FILE_SIZE:
        raise create_error_response(
            message=f"File size ({file.size} bytes) exceeds maximum allowed size ({MAX_FILE_SIZE} bytes)",
            error_code="FILE_TOO_LARGE",
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
        )
    
    # Validate content type
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise create_error_response(
            message=f"Invalid file type: {file.content_type}. Only PDF files are allowed.",
            error_code="INVALID_FILE_TYPE",
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    # Validate filename
    if not file.filename:
        raise create_error_response(
            message="Filename is required",
            error_code="MISSING_FILENAME",
            status_code=status.HTTP_400_BAD_REQUEST
        )


# Global error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Handle HTTP exceptions with standardized error response format.
    
    Requirements: 7.3, 7.4, 7.5 - Error handling and response formatting
    """
    # If detail is already a dict (from our custom HTTPExceptions), use it directly
    if isinstance(exc.detail, dict):
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.detail
        )
    
    # Otherwise, create standardized error response
    error_response = {
        "error": True,
        "message": str(exc.detail),
        "error_code": f"HTTP_{exc.status_code}",
        "timestamp": datetime.now().isoformat()
    }
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handle Pydantic validation errors with detailed error information.
    
    Requirements: 7.4 - Request validation error handling
    """
    error_details = []
    for error in exc.errors():
        error_details.append({
            "field": " -> ".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })
    
    error_response = {
        "error": True,
        "message": "Request validation failed",
        "error_code": "VALIDATION_ERROR",
        "timestamp": datetime.now().isoformat(),
        "details": error_details
    }
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response
    )


@app.exception_handler(ValidationError)
async def pydantic_validation_exception_handler(request: Request, exc: ValidationError):
    """
    Handle Pydantic model validation errors.
    
    Requirements: 7.4 - Data validation error handling
    """
    error_response = {
        "error": True,
        "message": "Data validation failed",
        "error_code": "MODEL_VALIDATION_ERROR",
        "timestamp": datetime.now().isoformat(),
        "details": exc.errors()
    }
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """
    Handle all other unexpected exceptions with generic error response.
    
    Requirements: 7.5 - General error handling
    """
    logger.error(f"Unexpected error: {exc}")
    logger.error(f"Traceback: {traceback.format_exc()}")
    
    error_response = {
        "error": True,
        "message": "An internal server error occurred",
        "error_code": "INTERNAL_SERVER_ERROR",
        "timestamp": datetime.now().isoformat()
    }
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response
    )


@app.get("/", response_model=APIInfo, summary="API Information", description="Get information about the Legal Case Similarity API")
async def root() -> APIInfo:
    """
    Get API information and available endpoints.
    
    Returns:
        API information including name, version, description, available endpoints,
        documentation link, and frontend URL
        
    Requirements: 2.2, 2.8, 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8
    """
    # Get frontend URL from environment variable
    frontend_url = os.getenv("FRONTEND_URL", "Configure FRONTEND_URL environment variable")
    
    return APIInfo(
        name="Legal Case Similarity API",
        version="1.0.0",
        description="API for finding similar legal cases using document similarity analysis",
        endpoints={
            "upload": "POST /api/upload - Upload PDF and find similar cases",
            "health": "GET /api/health - System health check",
            "performance": "GET /api/performance - Performance metrics",
            "case_details": "GET /api/cases/{case_id} - Get case details",
            "case_download": "GET /api/cases/{case_id}/download - Download case file"
        },
        documentation="/docs",
        frontend_url=frontend_url
    )


@app.post(
    "/api/upload",
    response_model=UploadResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Bad Request - Invalid file format"},
        413: {"model": ErrorResponse, "description": "Payload Too Large - File size exceeds limit"},
        422: {"model": ErrorResponse, "description": "Unprocessable Entity - PDF processing failed"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"}
    },
    summary="Upload PDF and find similar cases",
    description="Upload a PDF document and receive a list of similar legal cases ranked by similarity score"
)
async def upload_pdf(
    file: UploadFile = File(..., description="PDF file to analyze")
) -> UploadResponse:
    """
    Upload a PDF file and find similar legal cases.
    
    This endpoint:
    1. Validates the uploaded file is a PDF
    2. Extracts text content from the PDF
    3. Preprocesses the text for analysis
    4. Converts text to TF-IDF vector
    5. Searches for similar cases using cosine similarity
    6. Returns ranked list of similar cases
    
    Requirements: 7.1 - Upload endpoint functionality
    """
    start_time = datetime.now()
    query_id = f"query_{int(start_time.timestamp())}"
    
    # Track the entire upload operation
    with performance_monitor.track_operation(
        "upload_and_search",
        metadata={"query_id": query_id, "filename": file.filename}
    ):
        try:
            # Validate file upload
            validate_file_upload(file)
            
            # Read file content
            file_content = await file.read()
            
            # Validate PDF format using PDFProcessor
            if not pdf_processor.validate_pdf(file_content):
                raise create_error_response(
                    message="Invalid PDF file format or corrupted file",
                    error_code="INVALID_PDF_FORMAT",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            # Extract text from PDF with performance tracking
            with performance_monitor.track_operation("pdf_extraction"):
                try:
                    extracted_text = pdf_processor.extract_text_from_bytes(file_content, file.filename or "uploaded.pdf")
                except ValueError as e:
                    raise create_error_response(
                        message=f"Failed to extract text from PDF: {str(e)}",
                        error_code="PDF_EXTRACTION_FAILED",
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
                    )
            
            # Preprocess text with performance tracking
            with performance_monitor.track_operation("text_preprocessing"):
                try:
                    processed_text = text_preprocessor.preprocess(extracted_text)
                    if not processed_text.strip():
                        raise create_error_response(
                            message="No meaningful text content found in PDF after preprocessing",
                            error_code="NO_TEXT_CONTENT",
                            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
                        )
                except Exception as e:
                    raise create_error_response(
                        message=f"Text preprocessing failed: {str(e)}",
                        error_code="PREPROCESSING_FAILED",
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
            
            # Check if vectorizer is available and fitted
            if not vectorizer.is_fitted:
                raise create_error_response(
                    message="Vectorizer model is not available. Please contact system administrator.",
                    error_code="VECTORIZER_NOT_READY",
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # Convert text to vector with performance tracking
            with performance_monitor.track_operation("vectorization"):
                try:
                    query_vector = vectorizer.transform([processed_text])[0]
                except Exception as e:
                    raise create_error_response(
                        message=f"Text vectorization failed: {str(e)}",
                        error_code="VECTORIZATION_FAILED",
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
            
            # Check if similarity engine is available
            if similarity_engine is None:
                raise create_error_response(
                    message="No case repository available for similarity search",
                    error_code="NO_CASE_REPOSITORY",
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # Perform similarity search with performance tracking
            with performance_monitor.track_operation(
                "similarity_search",
                metadata={"case_count": similarity_engine.get_case_count()}
            ):
                try:
                    search_results = similarity_engine.search(query_vector, k=DEFAULT_RESULTS_COUNT)
                except Exception as e:
                    raise create_error_response(
                        message=f"Similarity search failed: {str(e)}",
                        error_code="SEARCH_FAILED",
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
            
            # Convert search results to response format
            similar_cases = []
            for result in search_results:
                similar_case = SimilarCase(
                    case_id=result.case_id,
                    title=result.title,
                    date=result.date,
                    similarity_score=result.similarity_score,
                    snippet=result.snippet,
                    download_url=f"/api/cases/{result.case_id}/download"
                )
                similar_cases.append(similar_case)
            
            # Calculate processing time
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            
            # Create response
            response = UploadResponse(
                results=similar_cases,
                processing_time=processing_time,
                query_id=query_id,
                total_cases_searched=similarity_engine.get_case_count()
            )
            
            logger.info(f"Successfully processed upload {query_id} in {processing_time:.2f}s, found {len(similar_cases)} results")
            return response
            
        except HTTPException:
            # Re-raise HTTP exceptions as-is
            raise
        except Exception as e:
            # Handle any unexpected errors
            logger.error(f"Unexpected error in upload endpoint: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise create_error_response(
                message="An unexpected error occurred during processing",
                error_code="INTERNAL_ERROR",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# Additional Pydantic models for new endpoints
class CaseDetail(BaseModel):
    """Model for detailed case information."""
    case_id: str = Field(..., description="Unique case identifier")
    title: str = Field(..., description="Case title")
    date: str = Field(..., description="Case date")
    file_path: str = Field(..., description="Path to case file")
    metadata: dict = Field(default_factory=dict, description="Additional case metadata")
    download_url: str = Field(..., description="URL to download case file")


class HealthStatus(BaseModel):
    """Model for system health status."""
    status: str = Field(..., description="System status")
    timestamp: str = Field(..., description="Status check timestamp")
    version: str = Field(..., description="API version")
    components: dict = Field(..., description="Component status information")
    statistics: dict = Field(..., description="System statistics")
    performance: dict = Field(default_factory=dict, description="Performance metrics")


class PerformanceStats(BaseModel):
    """Model for performance statistics."""
    operation_stats: dict = Field(..., description="Operation statistics")
    memory_stats: dict = Field(..., description="Memory usage statistics")
    concurrent_request_stats: dict = Field(..., description="Concurrent request statistics")
    recent_operations: List[dict] = Field(..., description="Recent operations")


@app.get(
    "/api/cases/{case_id}",
    response_model=CaseDetail,
    responses={
        404: {"model": ErrorResponse, "description": "Case not found"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"}
    },
    summary="Get case details by ID",
    description="Retrieve detailed information about a specific legal case by its unique identifier"
)
async def get_case_details(case_id: str) -> CaseDetail:
    """
    Get detailed information about a specific case.
    
    Args:
        case_id: Unique identifier for the case
        
    Returns:
        Detailed case information including metadata and download URL
        
    Requirements: 7.2 - Case details endpoint
    """
    try:
        # Retrieve case from repository
        case_document = case_repository.get_case_by_id(case_id)
        
        if case_document is None:
            raise create_error_response(
                message=f"Case with ID '{case_id}' not found",
                error_code="CASE_NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        # Create response model
        case_detail = CaseDetail(
            case_id=case_document.case_id,
            title=case_document.title,
            date=case_document.date.isoformat(),
            file_path=case_document.file_path,
            metadata=case_document.metadata or {},
            download_url=f"/api/cases/{case_id}/download"
        )
        
        return case_detail
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving case {case_id}: {e}")
        raise create_error_response(
            message=f"Failed to retrieve case details: {str(e)}",
            error_code="CASE_RETRIEVAL_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@app.get(
    "/api/cases/{case_id}/download",
    responses={
        200: {"description": "Case file download", "content": {"application/pdf": {}}},
        404: {"model": ErrorResponse, "description": "Case not found"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"}
    },
    summary="Download case file",
    description="Download the original PDF file for a specific legal case"
)
async def download_case_file(case_id: str):
    """
    Download the original PDF file for a case.
    
    Args:
        case_id: Unique identifier for the case
        
    Returns:
        PDF file as streaming response
        
    Requirements: 7.2 - Case file download
    """
    try:
        # Retrieve case from repository
        case_document = case_repository.get_case_by_id(case_id)
        
        if case_document is None:
            raise create_error_response(
                message=f"Case with ID '{case_id}' not found",
                error_code="CASE_NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        # Check if file exists
        file_path = Path(case_document.file_path)
        if not file_path.exists():
            raise create_error_response(
                message=f"Case file not found on disk: {case_document.file_path}",
                error_code="FILE_NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        # Return file as streaming response
        return FileResponse(
            path=str(file_path),
            media_type="application/pdf",
            filename=f"{case_id}.pdf"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading case file {case_id}: {e}")
        raise create_error_response(
            message=f"Failed to download case file: {str(e)}",
            error_code="FILE_DOWNLOAD_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@app.get(
    "/api/health",
    response_model=HealthStatus,
    summary="System health check",
    description="Get system health status and component information"
)
async def health_check() -> HealthStatus:
    """
    Get system health status and statistics.
    
    Returns:
        System health information including component status and statistics
        
    Requirements: 7.2 - Health monitoring endpoint, 6.8 - CORS configuration in health status
    """
    try:
        # Get CORS and frontend configuration
        cors_origins = os.getenv("CORS_ORIGINS", "*")
        frontend_url = os.getenv("FRONTEND_URL", "not_configured")
        
        # Check component status
        components = {
            "pdf_processor": "healthy",
            "text_preprocessor": "healthy",
            "vectorizer": "healthy" if vectorizer.is_fitted else "not_ready",
            "case_repository": "healthy",
            "similarity_engine": "healthy" if similarity_engine is not None else "not_available",
            "cors": "configured" if cors_origins != "*" else "development_mode"
        }
        
        # Get repository statistics
        case_count = case_repository.get_case_count()
        repository_validation = case_repository.validate_repository()
        
        statistics = {
            "total_cases": case_count,
            "repository_consistent": repository_validation.get("consistent", False),
            "vectorizer_fitted": vectorizer.is_fitted,
            "vector_dimensions": vectorizer.get_vector_dimension() if vectorizer.is_fitted else 0,
            "vocabulary_size": vectorizer.vocabulary_size,
            "max_repository_capacity": case_repository.MAX_REPOSITORY_SIZE,
            "cors_origins": cors_origins,
            "frontend_url": frontend_url
        }
        
        # Get performance metrics
        performance = {
            "concurrent_requests": performance_monitor.get_concurrent_request_stats(),
            "search_performance": performance_monitor.get_operation_stats("similarity_search"),
            "upload_performance": performance_monitor.get_operation_stats("upload_and_search")
        }
        
        # Determine overall system status
        overall_status = "healthy"
        if not vectorizer.is_fitted:
            overall_status = "degraded"
        elif similarity_engine is None:
            overall_status = "degraded"
        elif not repository_validation.get("consistent", False):
            overall_status = "degraded"
        
        health_status = HealthStatus(
            status=overall_status,
            timestamp=datetime.now().isoformat(),
            version="1.0.0",
            components=components,
            statistics=statistics,
            performance=performance
        )
        
        return health_status
        
    except Exception as e:
        logger.error(f"Error during health check: {e}")
        # Return degraded status instead of failing
        return HealthStatus(
            status="error",
            timestamp=datetime.now().isoformat(),
            version="1.0.0",
            components={"system": "error"},
            statistics={"error": str(e)},
            performance={}
        )


@app.get(
    "/api/performance",
    response_model=PerformanceStats,
    summary="Get performance metrics",
    description="Get detailed performance metrics including operation stats, memory usage, and concurrent request handling"
)
async def get_performance_metrics() -> PerformanceStats:
    """
    Get detailed performance metrics.
    
    Returns:
        Performance statistics including operation times, memory usage, and concurrency
        
    Requirements: 5.1, 5.2, 5.3 - Performance monitoring
    """
    try:
        summary = performance_monitor.get_summary()
        
        return PerformanceStats(
            operation_stats=summary["operation_stats"],
            memory_stats=summary["memory_stats"],
            concurrent_request_stats=summary["concurrent_request_stats"],
            recent_operations=summary["recent_operations"]
        )
        
    except Exception as e:
        logger.error(f"Error retrieving performance metrics: {e}")
        raise create_error_response(
            message=f"Failed to retrieve performance metrics: {str(e)}",
            error_code="PERFORMANCE_METRICS_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ============================================================================
# INQUIRY MANAGEMENT ENDPOINTS
# ============================================================================

@app.post(
    "/api/inquiries",
    response_model=InquiryResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Bad Request - Invalid inquiry data"},
        422: {"model": ErrorResponse, "description": "Unprocessable Entity - Validation failed"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"}
    },
    summary="Submit a legal inquiry",
    description="Submit a new legal inquiry with case details, personal information, and requirements"
)
async def create_inquiry(inquiry: InquiryCreate) -> InquiryResponse:
    """
    Create a new legal inquiry.
    
    This endpoint allows users to submit inquiries for legal consultation.
    The inquiry is stored in the backend for review by legal professionals.
    
    Args:
        inquiry: Inquiry data including case details, personal info, and requirements
        
    Returns:
        Created inquiry with generated ID and timestamps
    """
    try:
        # Convert Pydantic model to dict
        inquiry_data = inquiry.dict()
        
        # Create inquiry in repository
        created_inquiry = inquiry_repository.create_inquiry(inquiry_data)
        
        # Convert to response model
        response = InquiryResponse(**created_inquiry)
        
        logger.info(f"Created inquiry {response.inquiry_id} for {response.full_name}")
        
        return response
        
    except ValidationError as e:
        logger.error(f"Validation error creating inquiry: {e}")
        raise create_error_response(
            message=f"Inquiry validation failed: {str(e)}",
            error_code="INQUIRY_VALIDATION_ERROR",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
        )
    except Exception as e:
        logger.error(f"Error creating inquiry: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise create_error_response(
            message=f"Failed to create inquiry: {str(e)}",
            error_code="INQUIRY_CREATION_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@app.get(
    "/api/inquiries",
    response_model=InquiryListResponse,
    summary="Get all inquiries",
    description="Retrieve all legal inquiries with optional filtering by status"
)
async def get_inquiries(
    status: Optional[str] = None,
    limit: Optional[int] = 50,
    offset: int = 0
) -> InquiryListResponse:
    """
    Get all inquiries with optional filtering.
    
    Args:
        status: Filter by status (pending, reviewed, contacted, closed)
        limit: Maximum number of inquiries to return
        offset: Number of inquiries to skip
        
    Returns:
        List of inquiries with total count
    """
    try:
        inquiries = inquiry_repository.get_all_inquiries(
            status=status,
            limit=limit,
            offset=offset
        )
        
        # Convert to response models
        inquiry_responses = [InquiryResponse(**inq) for inq in inquiries]
        
        # Get total count (without pagination)
        all_inquiries = inquiry_repository.get_all_inquiries(status=status)
        total = len(all_inquiries)
        
        return InquiryListResponse(
            total=total,
            inquiries=inquiry_responses
        )
        
    except Exception as e:
        logger.error(f"Error retrieving inquiries: {e}")
        raise create_error_response(
            message=f"Failed to retrieve inquiries: {str(e)}",
            error_code="INQUIRY_RETRIEVAL_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@app.get(
    "/api/inquiries/{inquiry_id}",
    response_model=InquiryResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Inquiry not found"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"}
    },
    summary="Get inquiry by ID",
    description="Retrieve a specific inquiry by its unique identifier"
)
async def get_inquiry(inquiry_id: str) -> InquiryResponse:
    """
    Get a specific inquiry by ID.
    
    Args:
        inquiry_id: Unique inquiry identifier
        
    Returns:
        Inquiry details
    """
    try:
        inquiry = inquiry_repository.get_inquiry(inquiry_id)
        
        if inquiry is None:
            raise create_error_response(
                message=f"Inquiry with ID '{inquiry_id}' not found",
                error_code="INQUIRY_NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        return InquiryResponse(**inquiry)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving inquiry {inquiry_id}: {e}")
        raise create_error_response(
            message=f"Failed to retrieve inquiry: {str(e)}",
            error_code="INQUIRY_RETRIEVAL_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@app.patch(
    "/api/inquiries/{inquiry_id}/status",
    response_model=InquiryResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Inquiry not found"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"}
    },
    summary="Update inquiry status",
    description="Update the status of an inquiry (pending, reviewed, contacted, closed)"
)
async def update_inquiry_status(
    inquiry_id: str,
    status: str
) -> InquiryResponse:
    """
    Update inquiry status.
    
    Args:
        inquiry_id: Unique inquiry identifier
        status: New status (pending, reviewed, contacted, closed)
        
    Returns:
        Updated inquiry
    """
    try:
        # Validate status
        valid_statuses = ["pending", "reviewed", "contacted", "closed"]
        if status not in valid_statuses:
            raise create_error_response(
                message=f"Invalid status. Must be one of: {', '.join(valid_statuses)}",
                error_code="INVALID_STATUS",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        updated_inquiry = inquiry_repository.update_inquiry_status(inquiry_id, status)
        
        if updated_inquiry is None:
            raise create_error_response(
                message=f"Inquiry with ID '{inquiry_id}' not found",
                error_code="INQUIRY_NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        logger.info(f"Updated inquiry {inquiry_id} status to {status}")
        
        return InquiryResponse(**updated_inquiry)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating inquiry status {inquiry_id}: {e}")
        raise create_error_response(
            message=f"Failed to update inquiry status: {str(e)}",
            error_code="INQUIRY_UPDATE_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@app.delete(
    "/api/inquiries/{inquiry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        404: {"model": ErrorResponse, "description": "Inquiry not found"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"}
    },
    summary="Delete inquiry",
    description="Delete an inquiry by its unique identifier"
)
async def delete_inquiry(inquiry_id: str):
    """
    Delete an inquiry.
    
    Args:
        inquiry_id: Unique inquiry identifier
    """
    try:
        deleted = inquiry_repository.delete_inquiry(inquiry_id)
        
        if not deleted:
            raise create_error_response(
                message=f"Inquiry with ID '{inquiry_id}' not found",
                error_code="INQUIRY_NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        logger.info(f"Deleted inquiry {inquiry_id}")
        
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting inquiry {inquiry_id}: {e}")
        raise create_error_response(
            message=f"Failed to delete inquiry: {str(e)}",
            error_code="INQUIRY_DELETE_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@app.get(
    "/api/inquiries/stats/summary",
    summary="Get inquiry statistics",
    description="Get statistical summary of all inquiries"
)
async def get_inquiry_statistics():
    """
    Get inquiry statistics.
    
    Returns:
        Statistical summary including counts by status, urgency, and case type
    """
    try:
        stats = inquiry_repository.get_statistics()
        return stats
        
    except Exception as e:
        logger.error(f"Error retrieving inquiry statistics: {e}")
        raise create_error_response(
            message=f"Failed to retrieve inquiry statistics: {str(e)}",
            error_code="INQUIRY_STATS_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ============================================================================
# HELPER CASE ENDPOINTS
# ============================================================================

class HelperCaseMetadata(BaseModel):
    """Metadata for helper case submission."""
    user_id: str
    title: str
    case_type: str
    description: str
    outcome: str
    duration_months: int
    total_cost: float
    court_name: str
    state: str
    city: str
    lawyer_name: Optional[str] = None
    lawyer_contact: Optional[str] = None
    key_learnings: Optional[str] = None
    advice_for_others: Optional[str] = None
    is_public: bool = True
    willing_to_help: bool = True


class HelperCaseResponse(BaseModel):
    """Response model for helper case submission."""
    case_id: str
    title: str
    case_type: str
    outcome: str
    message: str
    similar_cases_count: Optional[int] = None
    processing_time: float


@app.post(
    "/api/helper/cases",
    response_model=HelperCaseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit helper case",
    description="Submit a case from an experienced litigant (helper) to help others"
)
async def submit_helper_case(
    file: UploadFile = File(..., description="PDF document of the case"),
    metadata: str = File(..., description="JSON string with case metadata")
):
    """
    Submit a case from a helper user.
    
    This endpoint allows experienced litigants to share their case details
    to help others facing similar situations.
    
    Args:
        file: PDF file containing case document
        metadata: JSON string with case metadata
        
    Returns:
        HelperCaseResponse with case details and processing info
    """
    import json
    from src.models.helper_case import HelperCase
    
    temp_file_path = None
    query_id = f"helper_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    try:
        # Parse metadata
        try:
            metadata_dict = json.loads(metadata)
            case_metadata = HelperCaseMetadata(**metadata_dict)
        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid metadata JSON: {str(e)}"
            )
        except ValidationError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid metadata: {str(e)}"
            )
        
        # Validate file
        validate_file_upload(file)
        
        start_time = datetime.now()
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        logger.info(f"Processing helper case upload: {file.filename}")
        
        # Extract text from PDF
        with performance_monitor.track_operation("pdf_extraction"):
            extracted_text = pdf_processor.extract_text(temp_file_path)
        
        if not extracted_text or len(extracted_text.strip()) < 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not extract sufficient text from PDF. Please ensure the PDF contains readable text."
            )
        
        # Preprocess text
        with performance_monitor.track_operation("text_preprocessing"):
            processed_text = text_preprocessor.preprocess(extracted_text)
        
        # Vectorize the document
        with performance_monitor.track_operation("vectorization"):
            query_vector = vectorizer.transform([processed_text])[0]
        
        # Generate case ID
        case_id = f"case_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{case_metadata.user_id[:8]}"
        
        # Save case document to repository
        case_file_path = Path("data/cases") / f"{case_id}.pdf"
        case_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Copy file to permanent location
        import shutil
        shutil.copy2(temp_file_path, case_file_path)
        
        # Create HelperCase object
        helper_case = HelperCase(
            case_id=case_id,
            user_id=case_metadata.user_id,
            title=case_metadata.title,
            case_type=case_metadata.case_type,
            description=case_metadata.description,
            outcome=case_metadata.outcome,
            duration_months=case_metadata.duration_months,
            total_cost=case_metadata.total_cost,
            court_name=case_metadata.court_name,
            state=case_metadata.state,
            city=case_metadata.city,
            lawyer_name=case_metadata.lawyer_name,
            lawyer_contact=case_metadata.lawyer_contact,
            key_learnings=case_metadata.key_learnings,
            advice_for_others=case_metadata.advice_for_others,
            file_path=str(case_file_path),
            text_content=extracted_text,
            vector=query_vector,
            is_public=case_metadata.is_public,
            willing_to_help=case_metadata.willing_to_help
        )
        
        # Save case metadata to JSON
        cases_metadata_path = Path("data/helper_cases_metadata.json")
        if cases_metadata_path.exists():
            with open(cases_metadata_path, 'r', encoding='utf-8') as f:
                all_cases = json.load(f)
        else:
            all_cases = []
        
        all_cases.append(helper_case.to_dict())
        
        with open(cases_metadata_path, 'w', encoding='utf-8') as f:
            json.dump(all_cases, f, indent=2, ensure_ascii=False)
        
        # Save vector for future similarity searches
        import pickle
        import numpy as np
        
        vectors_path = Path("data/vectors/helper_case_vectors.pkl")
        vectors_path.parent.mkdir(parents=True, exist_ok=True)
        
        if vectors_path.exists():
            with open(vectors_path, 'rb') as f:
                existing_vectors = pickle.load(f)
            existing_vectors[case_id] = query_vector
        else:
            existing_vectors = {case_id: query_vector}
        
        with open(vectors_path, 'wb') as f:
            pickle.dump(existing_vectors, f)
        
        # Find similar cases (optional, for statistics)
        similar_count = 0
        if similarity_engine:
            try:
                similar_cases = similarity_engine.search(query_vector, k=5)
                similar_count = len(similar_cases)
            except Exception as e:
                logger.warning(f"Could not find similar cases: {e}")
        
        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds()
        
        logger.info(f"Successfully processed helper case {case_id} in {processing_time:.2f}s")
        
        return HelperCaseResponse(
            case_id=case_id,
            title=case_metadata.title,
            case_type=case_metadata.case_type,
            outcome=case_metadata.outcome,
            message="Case submitted successfully and added to database",
            similar_cases_count=similar_count,
            processing_time=processing_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing helper case: {e}")
        logger.error(traceback.format_exc())
        raise create_error_response(
            message=f"Failed to process case: {str(e)}",
            error_code="HELPER_CASE_PROCESSING_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    finally:
        # Clean up temporary file
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except Exception as e:
                logger.warning(f"Failed to delete temporary file: {e}")


@app.get(
    "/api/helper/cases",
    summary="Get all helper cases",
    description="Retrieve all cases submitted by helpers"
)
async def get_helper_cases(
    user_id: Optional[str] = None,
    case_type: Optional[str] = None,
    outcome: Optional[str] = None,
    state: Optional[str] = None,
    is_public: bool = True
):
    """
    Get all helper cases with optional filtering.
    
    Args:
        user_id: Filter by user ID
        case_type: Filter by case type
        outcome: Filter by outcome
        state: Filter by state
        is_public: Filter by public visibility
        
    Returns:
        List of helper cases
    """
    import json
    
    try:
        cases_metadata_path = Path("data/helper_cases_metadata.json")
        
        if not cases_metadata_path.exists():
            return []
        
        with open(cases_metadata_path, 'r', encoding='utf-8') as f:
            all_cases = json.load(f)
        
        # Apply filters
        filtered_cases = all_cases
        
        if user_id:
            filtered_cases = [c for c in filtered_cases if c.get('user_id') == user_id]
        
        if case_type:
            filtered_cases = [c for c in filtered_cases if c.get('case_type') == case_type]
        
        if outcome:
            filtered_cases = [c for c in filtered_cases if c.get('outcome') == outcome]
        
        if state:
            filtered_cases = [c for c in filtered_cases if c.get('state') == state]
        
        if is_public:
            filtered_cases = [c for c in filtered_cases if c.get('is_public', True)]
        
        return filtered_cases
        
    except Exception as e:
        logger.error(f"Error retrieving helper cases: {e}")
        raise create_error_response(
            message=f"Failed to retrieve cases: {str(e)}",
            error_code="HELPER_CASES_RETRIEVAL_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@app.post(
    "/api/search/enhanced",
    summary="Enhanced search with helper profiles",
    description="Search for similar cases and include helper user profiles in results"
)
async def enhanced_search(
    file: UploadFile = File(..., description="PDF file to analyze"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Enhanced search that includes helper user profiles in results.
    
    This endpoint:
    1. Performs similarity search (same as /api/upload)
    2. Loads helper case metadata
    3. Fetches user profiles for helpers
    4. Returns enriched results with user information
    """
    import json
    import pickle
    import numpy as np
    from src.api.auth_routes import get_current_user
    
    start_time = datetime.now()
    query_id = f"enhanced_query_{int(start_time.timestamp())}"
    
    try:
        # Validate file upload
        validate_file_upload(file)
        
        # Read and process file (same as regular upload)
        file_content = await file.read()
        
        if not pdf_processor.validate_pdf(file_content):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid PDF file format"
            )
        
        # Extract and preprocess text
        extracted_text = pdf_processor.extract_text_from_bytes(file_content, file.filename or "uploaded.pdf")
        processed_text = text_preprocessor.preprocess(extracted_text)
        
        if not processed_text.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="No meaningful text content found in PDF"
            )
        
        # Vectorize
        query_vector = vectorizer.transform([processed_text])[0]
        
        # Search in original cases
        original_results = []
        if similarity_engine:
            original_results = similarity_engine.search(query_vector, k=10)
        
        # Search in helper cases
        helper_results = []
        helper_cases_path = Path("data/helper_cases_metadata.json")
        helper_vectors_path = Path("data/vectors/helper_case_vectors.pkl")
        
        if helper_cases_path.exists() and helper_vectors_path.exists():
            # Load helper cases metadata
            with open(helper_cases_path, 'r', encoding='utf-8') as f:
                helper_cases = json.load(f)
            
            # Load helper case vectors
            with open(helper_vectors_path, 'rb') as f:
                helper_vectors = pickle.load(f)
            
            # Calculate similarity for each helper case
            from sklearn.metrics.pairwise import cosine_similarity
            
            for case in helper_cases:
                if not case.get('is_public', True):
                    continue
                
                case_id = case['case_id']
                if case_id in helper_vectors:
                    case_vector = helper_vectors[case_id]
                    similarity = cosine_similarity([query_vector], [case_vector])[0][0]
                    
                    if similarity > 0.1:  # Minimum threshold
                        # Fetch user profile
                        user = db.query(User).filter(User.user_id == case['user_id']).first()
                        
                        helper_results.append({
                            'case_id': case_id,
                            'title': case['title'],
                            'similarity_score': float(similarity),
                            'case_type': case['case_type'],
                            'outcome': case['outcome'],
                            'duration_months': case['duration_months'],
                            'total_cost': case['total_cost'],
                            'court_name': case['court_name'],
                            'state': case['state'],
                            'city': case['city'],
                            'key_learnings': case.get('key_learnings'),
                            'advice_for_others': case.get('advice_for_others'),
                            'helper_info': {
                                'user_id': user.user_id if user else None,
                                'full_name': user.full_name if user else 'Anonymous',
                                'reputation_score': user.reputation_score if user else 0.0,
                                'cases_helped': user.cases_helped if user else 0,
                                'total_ratings': user.total_ratings if user else 0,
                                'city': user.city if user else None,
                                'state': user.state if user else None,
                                'willing_to_help': case.get('willing_to_help', True)
                            } if user else None
                        })
        
        # Combine and sort results
        all_results = []
        
        # Add original cases
        for result in original_results:
            all_results.append({
                'case_id': result.case_id,
                'title': result.title,
                'similarity_score': result.similarity_score,
                'snippet': result.snippet,
                'date': result.date,
                'source': 'original',
                'helper_info': None
            })
        
        # Add helper cases
        for result in helper_results:
            all_results.append({
                **result,
                'source': 'helper',
                'snippet': result.get('key_learnings', '')[:200] if result.get('key_learnings') else ''
            })
        
        # Sort by similarity score
        all_results.sort(key=lambda x: x['similarity_score'], reverse=True)
        
        # Take top 10
        all_results = all_results[:10]
        
        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds()
        
        logger.info(f"Enhanced search {query_id} completed in {processing_time:.2f}s, found {len(all_results)} results")
        
        return {
            'results': all_results,
            'processing_time': processing_time,
            'query_id': query_id,
            'total_results': len(all_results),
            'helper_cases_count': len(helper_results),
            'original_cases_count': len(original_results)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in enhanced search: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Enhanced search failed: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


# ============================================================================
# CONNECTION MANAGEMENT ENDPOINTS
# ============================================================================

class ConnectionRequest(BaseModel):
    """Request model for creating a connection."""
    helper_id: str = Field(..., description="ID of the helper user")
    helper_case_id: Optional[str] = Field(None, description="ID of the helper's case")
    message: Optional[str] = Field(None, description="Optional message to the helper")


class ConnectionResponse(BaseModel):
    """Response model for connection."""
    connection_id: str
    requester_id: str
    helper_id: str
    status: str
    message: Optional[str]
    created_at: str
    requester_info: Optional[dict] = None
    helper_info: Optional[dict] = None


@app.post(
    "/api/connections/request",
    response_model=ConnectionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Send connection request",
    description="Send a connection request to a helper user"
)
async def create_connection_request(
    connection_request: ConnectionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a connection request from seeker to helper.
    
    Args:
        connection_request: Connection request details
        current_user: Authenticated user (requester)
        db: Database session
        
    Returns:
        Created connection with user information
    """
    from src.models.connection import Connection
    
    try:
        # Validate helper exists
        helper = db.query(User).filter(User.user_id == connection_request.helper_id).first()
        if not helper:
            raise create_error_response(
                message="Helper user not found",
                error_code="HELPER_NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        # Check if connection already exists
        existing_connection = db.query(Connection).filter(
            Connection.requester_id == current_user.user_id,
            Connection.helper_id == connection_request.helper_id,
            Connection.status.in_(['pending', 'accepted'])
        ).first()
        
        if existing_connection:
            raise create_error_response(
                message="Connection request already exists",
                error_code="CONNECTION_EXISTS",
                status_code=status.HTTP_409_CONFLICT
            )
        
        # Create connection
        connection_id = f"conn_{datetime.now().strftime('%Y%m%d%H%M%S')}_{current_user.user_id[:8]}"
        
        new_connection = Connection(
            connection_id=connection_id,
            requester_id=current_user.user_id,
            helper_id=connection_request.helper_id,
            helper_case_id=connection_request.helper_case_id,
            message=connection_request.message,
            status='pending'
        )
        
        db.add(new_connection)
        db.commit()
        db.refresh(new_connection)
        
        logger.info(f"Connection request created: {connection_id}")
        
        # Prepare response with user info
        response = ConnectionResponse(
            connection_id=new_connection.connection_id,
            requester_id=new_connection.requester_id,
            helper_id=new_connection.helper_id,
            status=new_connection.status,
            message=new_connection.message,
            created_at=new_connection.created_at.isoformat(),
            requester_info={
                'user_id': current_user.user_id,
                'full_name': current_user.full_name,
                'email': current_user.email
            },
            helper_info={
                'user_id': helper.user_id,
                'full_name': helper.full_name,
                'email': helper.email
            }
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating connection request: {e}")
        logger.error(traceback.format_exc())
        raise create_error_response(
            message=f"Failed to create connection request: {str(e)}",
            error_code="CONNECTION_REQUEST_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@app.get(
    "/api/connections/pending",
    summary="Get pending connection requests",
    description="Get all pending connection requests for the current user"
)
async def get_pending_connections(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get pending connection requests.
    
    For helpers: Get requests they received
    For seekers: Get requests they sent
    
    Args:
        current_user: Authenticated user
        db: Database session
        
    Returns:
        List of pending connections with user information
    """
    try:
        from src.models.connection import Connection
        
        if current_user.user_type == 'helper':
            # Get requests received by helper
            connections = db.query(Connection).filter(
                Connection.helper_id == current_user.user_id,
                Connection.status == 'pending'
            ).all()
            
            # Add requester info
            results = []
            for conn in connections:
                requester = db.query(User).filter(User.user_id == conn.requester_id).first()
                results.append({
                    **conn.to_dict(),
                    'requester_info': {
                        'user_id': requester.user_id,
                        'full_name': requester.full_name,
                        'email': requester.email,
                        'city': requester.city,
                        'state': requester.state
                    } if requester else None
                })
        else:
            # Get requests sent by seeker
            connections = db.query(Connection).filter(
                Connection.requester_id == current_user.user_id,
                Connection.status == 'pending'
            ).all()
            
            # Add helper info
            results = []
            for conn in connections:
                helper = db.query(User).filter(User.user_id == conn.helper_id).first()
                results.append({
                    **conn.to_dict(),
                    'helper_info': {
                        'user_id': helper.user_id,
                        'full_name': helper.full_name,
                        'email': helper.email,
                        'reputation_score': helper.reputation_score,
                        'cases_helped': helper.cases_helped
                    } if helper else None
                })
        
        return {'connections': results, 'count': len(results)}
        
    except Exception as e:
        logger.error(f"Error retrieving pending connections: {e}")
        raise create_error_response(
            message=f"Failed to retrieve connections: {str(e)}",
            error_code="CONNECTION_RETRIEVAL_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@app.get(
    "/api/connections/accepted",
    summary="Get accepted connections",
    description="Get all accepted connections for the current user"
)
async def get_accepted_connections(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get accepted connections for the current user.
    
    Args:
        current_user: Authenticated user
        db: Database session
        
    Returns:
        List of accepted connections with user information
    """
    try:
        from src.models.connection import Connection
        
        # Get connections where user is either requester or helper
        connections = db.query(Connection).filter(
            ((Connection.requester_id == current_user.user_id) | 
             (Connection.helper_id == current_user.user_id)),
            Connection.status == 'accepted'
        ).all()
        
        # Add other user's info
        results = []
        for conn in connections:
            if conn.requester_id == current_user.user_id:
                # Current user is requester, get helper info
                other_user = db.query(User).filter(User.user_id == conn.helper_id).first()
                role = 'helper'
            else:
                # Current user is helper, get requester info
                other_user = db.query(User).filter(User.user_id == conn.requester_id).first()
                role = 'requester'
            
            results.append({
                **conn.to_dict(),
                'other_user': {
                    'user_id': other_user.user_id,
                    'full_name': other_user.full_name,
                    'email': other_user.email,
                    'user_type': other_user.user_type,
                    'city': other_user.city,
                    'state': other_user.state,
                    'reputation_score': other_user.reputation_score if other_user.user_type == 'helper' else None
                } if other_user else None,
                'role': role
            })
        
        return {'connections': results, 'count': len(results)}
        
    except Exception as e:
        logger.error(f"Error retrieving accepted connections: {e}")
        raise create_error_response(
            message=f"Failed to retrieve connections: {str(e)}",
            error_code="CONNECTION_RETRIEVAL_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@app.patch(
    "/api/connections/{connection_id}/accept",
    summary="Accept connection request",
    description="Accept a pending connection request (helpers only)"
)
async def accept_connection(
    connection_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Accept a connection request.
    
    Args:
        connection_id: Connection ID to accept
        current_user: Authenticated user (must be the helper)
        db: Database session
        
    Returns:
        Updated connection
    """
    try:
        from src.models.connection import Connection
        
        # Get connection
        connection = db.query(Connection).filter(
            Connection.connection_id == connection_id
        ).first()
        
        if not connection:
            raise create_error_response(
                message="Connection not found",
                error_code="CONNECTION_NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        # Verify current user is the helper
        if connection.helper_id != current_user.user_id:
            raise create_error_response(
                message="Only the helper can accept this connection",
                error_code="UNAUTHORIZED_ACTION",
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        # Verify status is pending
        if connection.status != 'pending':
            raise create_error_response(
                message=f"Connection is already {connection.status}",
                error_code="INVALID_STATUS",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        # Update connection
        connection.status = 'accepted'
        connection.accepted_at = datetime.utcnow()
        
        # Update helper's cases_helped count
        current_user.cases_helped = (current_user.cases_helped or 0) + 1
        
        db.commit()
        db.refresh(connection)
        
        logger.info(f"Connection accepted: {connection_id}")
        
        return {'message': 'Connection accepted successfully', 'connection': connection.to_dict()}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error accepting connection: {e}")
        raise create_error_response(
            message=f"Failed to accept connection: {str(e)}",
            error_code="CONNECTION_ACCEPT_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@app.patch(
    "/api/connections/{connection_id}/decline",
    summary="Decline connection request",
    description="Decline a pending connection request (helpers only)"
)
async def decline_connection(
    connection_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Decline a connection request.
    
    Args:
        connection_id: Connection ID to decline
        current_user: Authenticated user (must be the helper)
        db: Database session
        
    Returns:
        Updated connection
    """
    try:
        from src.models.connection import Connection
        
        # Get connection
        connection = db.query(Connection).filter(
            Connection.connection_id == connection_id
        ).first()
        
        if not connection:
            raise create_error_response(
                message="Connection not found",
                error_code="CONNECTION_NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        # Verify current user is the helper
        if connection.helper_id != current_user.user_id:
            raise create_error_response(
                message="Only the helper can decline this connection",
                error_code="UNAUTHORIZED_ACTION",
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        # Verify status is pending
        if connection.status != 'pending':
            raise create_error_response(
                message=f"Connection is already {connection.status}",
                error_code="INVALID_STATUS",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        # Update connection
        connection.status = 'declined'
        
        db.commit()
        db.refresh(connection)
        
        logger.info(f"Connection declined: {connection_id}")
        
        return {'message': 'Connection declined', 'connection': connection.to_dict()}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error declining connection: {e}")
        raise create_error_response(
            message=f"Failed to decline connection: {str(e)}",
            error_code="CONNECTION_DECLINE_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@app.delete(
    "/api/connections/{connection_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete connection",
    description="Delete a connection (requester can cancel pending, both can remove accepted)"
)
async def delete_connection(
    connection_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a connection.
    
    Args:
        connection_id: Connection ID to delete
        current_user: Authenticated user
        db: Database session
    """
    try:
        from src.models.connection import Connection
        
        # Get connection
        connection = db.query(Connection).filter(
            Connection.connection_id == connection_id
        ).first()
        
        if not connection:
            raise create_error_response(
                message="Connection not found",
                error_code="CONNECTION_NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        # Verify user is part of the connection
        if connection.requester_id != current_user.user_id and connection.helper_id != current_user.user_id:
            raise create_error_response(
                message="You don't have permission to delete this connection",
                error_code="UNAUTHORIZED_ACTION",
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        # Delete connection
        db.delete(connection)
        db.commit()
        
        logger.info(f"Connection deleted: {connection_id}")
        
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting connection: {e}")
        raise create_error_response(
            message=f"Failed to delete connection: {str(e)}",
            error_code="CONNECTION_DELETE_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ============================================================================
# MESSAGING ENDPOINTS
# ============================================================================

class MessageCreate(BaseModel):
    """Request model for creating a message."""
    connection_id: str = Field(..., description="ID of the connection")
    content: str = Field(..., min_length=1, max_length=5000, description="Message content")


class MessageResponse(BaseModel):
    """Response model for message."""
    message_id: str
    connection_id: str
    sender_id: str
    receiver_id: str
    content: str
    is_read: bool
    created_at: str
    read_at: Optional[str] = None
    sender_info: Optional[dict] = None


@app.post(
    "/api/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Send a message",
    description="Send a message to a connected user"
)
async def send_message(
    message_data: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Send a message to a connected user.
    
    Args:
        message_data: Message content and connection ID
        current_user: Authenticated user (sender)
        db: Database session
        
    Returns:
        Created message with sender information
    """
    try:
        from src.models.connection import Connection
        from src.models.message import Message
        
        # Verify connection exists and user is part of it
        connection = db.query(Connection).filter(
            Connection.connection_id == message_data.connection_id
        ).first()
        
        if not connection:
            raise create_error_response(
                message="Connection not found",
                error_code="CONNECTION_NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        # Verify connection is accepted
        if connection.status != 'accepted':
            raise create_error_response(
                message="Can only message accepted connections",
                error_code="CONNECTION_NOT_ACCEPTED",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        # Verify user is part of the connection
        if current_user.user_id not in [connection.requester_id, connection.helper_id]:
            raise create_error_response(
                message="You are not part of this connection",
                error_code="UNAUTHORIZED_CONNECTION",
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        # Determine receiver
        receiver_id = connection.helper_id if current_user.user_id == connection.requester_id else connection.requester_id
        
        # Create message
        message_id = f"msg_{datetime.now().strftime('%Y%m%d%H%M%S')}_{current_user.user_id[:8]}"
        
        new_message = Message(
            message_id=message_id,
            connection_id=message_data.connection_id,
            sender_id=current_user.user_id,
            receiver_id=receiver_id,
            content=message_data.content,
            is_read=False
        )
        
        db.add(new_message)
        db.commit()
        db.refresh(new_message)
        
        logger.info(f"Message sent: {message_id}")
        
        # Prepare response
        response = MessageResponse(
            message_id=new_message.message_id,
            connection_id=new_message.connection_id,
            sender_id=new_message.sender_id,
            receiver_id=new_message.receiver_id,
            content=new_message.content,
            is_read=new_message.is_read,
            created_at=new_message.created_at.isoformat(),
            read_at=new_message.read_at.isoformat() if new_message.read_at else None,
            sender_info={
                'user_id': current_user.user_id,
                'full_name': current_user.full_name
            }
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        logger.error(traceback.format_exc())
        raise create_error_response(
            message=f"Failed to send message: {str(e)}",
            error_code="MESSAGE_SEND_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@app.get(
    "/api/messages/conversation/{connection_id}",
    summary="Get conversation messages",
    description="Get all messages for a specific connection"
)
async def get_conversation(
    connection_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all messages for a connection.
    
    Args:
        connection_id: Connection ID
        current_user: Authenticated user
        db: Database session
        
    Returns:
        List of messages with user information
    """
    try:
        from src.models.connection import Connection
        from src.models.message import Message
        
        # Verify connection exists and user is part of it
        connection = db.query(Connection).filter(
            Connection.connection_id == connection_id
        ).first()
        
        if not connection:
            raise create_error_response(
                message="Connection not found",
                error_code="CONNECTION_NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        # Verify user is part of the connection
        if current_user.user_id not in [connection.requester_id, connection.helper_id]:
            raise create_error_response(
                message="You are not part of this connection",
                error_code="UNAUTHORIZED_CONNECTION",
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        # Get all messages for this connection
        messages = db.query(Message).filter(
            Message.connection_id == connection_id
        ).order_by(Message.created_at.asc()).all()
        
        # Mark messages as read if current user is receiver
        for message in messages:
            if message.receiver_id == current_user.user_id and not message.is_read:
                message.is_read = True
                message.read_at = datetime.utcnow()
        
        db.commit()
        
        # Get user info for all participants
        requester = db.query(User).filter(User.user_id == connection.requester_id).first()
        helper = db.query(User).filter(User.user_id == connection.helper_id).first()
        
        # Prepare response
        results = []
        for msg in messages:
            sender = requester if msg.sender_id == connection.requester_id else helper
            results.append({
                **msg.to_dict(),
                'sender_info': {
                    'user_id': sender.user_id,
                    'full_name': sender.full_name,
                    'user_type': sender.user_type
                } if sender else None
            })
        
        return {
            'messages': results,
            'count': len(results),
            'connection': {
                'connection_id': connection.connection_id,
                'requester': {
                    'user_id': requester.user_id,
                    'full_name': requester.full_name,
                    'user_type': requester.user_type
                } if requester else None,
                'helper': {
                    'user_id': helper.user_id,
                    'full_name': helper.full_name,
                    'user_type': helper.user_type,
                    'reputation_score': helper.reputation_score
                } if helper else None
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving conversation: {e}")
        raise create_error_response(
            message=f"Failed to retrieve conversation: {str(e)}",
            error_code="CONVERSATION_RETRIEVAL_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@app.get(
    "/api/messages/conversations",
    summary="Get all conversations",
    description="Get list of all conversations for the current user"
)
async def get_conversations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all conversations for the current user.
    
    Args:
        current_user: Authenticated user
        db: Database session
        
    Returns:
        List of conversations with last message and unread count
    """
    try:
        from src.models.connection import Connection
        from src.models.message import Message
        
        # Get all accepted connections for user
        connections = db.query(Connection).filter(
            ((Connection.requester_id == current_user.user_id) | 
             (Connection.helper_id == current_user.user_id)),
            Connection.status == 'accepted'
        ).all()
        
        conversations = []
        for conn in connections:
            # Get other user
            other_user_id = conn.helper_id if current_user.user_id == conn.requester_id else conn.requester_id
            other_user = db.query(User).filter(User.user_id == other_user_id).first()
            
            # Get last message
            last_message = db.query(Message).filter(
                Message.connection_id == conn.connection_id
            ).order_by(Message.created_at.desc()).first()
            
            # Get unread count
            unread_count = db.query(Message).filter(
                Message.connection_id == conn.connection_id,
                Message.receiver_id == current_user.user_id,
                Message.is_read == False
            ).count()
            
            conversations.append({
                'connection_id': conn.connection_id,
                'other_user': {
                    'user_id': other_user.user_id,
                    'full_name': other_user.full_name,
                    'user_type': other_user.user_type,
                    'reputation_score': other_user.reputation_score if other_user.user_type == 'helper' else None
                } if other_user else None,
                'last_message': {
                    'content': last_message.content,
                    'created_at': last_message.created_at.isoformat(),
                    'sender_id': last_message.sender_id,
                    'is_read': last_message.is_read
                } if last_message else None,
                'unread_count': unread_count,
                'created_at': conn.created_at.isoformat()
            })
        
        # Sort by last message time (most recent first)
        conversations.sort(key=lambda x: x['last_message']['created_at'] if x['last_message'] else x['created_at'], reverse=True)
        
        return {'conversations': conversations, 'count': len(conversations)}
        
    except Exception as e:
        logger.error(f"Error retrieving conversations: {e}")
        raise create_error_response(
            message=f"Failed to retrieve conversations: {str(e)}",
            error_code="CONVERSATIONS_RETRIEVAL_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@app.get(
    "/api/messages/unread",
    summary="Get unread message count",
    description="Get total count of unread messages"
)
async def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get unread message count for current user.
    
    Args:
        current_user: Authenticated user
        db: Database session
        
    Returns:
        Unread message count
    """
    try:
        from src.models.message import Message
        
        unread_count = db.query(Message).filter(
            Message.receiver_id == current_user.user_id,
            Message.is_read == False
        ).count()
        
        return {'unread_count': unread_count}
        
    except Exception as e:
        logger.error(f"Error retrieving unread count: {e}")
        raise create_error_response(
            message=f"Failed to retrieve unread count: {str(e)}",
            error_code="UNREAD_COUNT_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@app.delete(
    "/api/messages/{message_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete message",
    description="Delete a message (sender only)"
)
async def delete_message(
    message_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a message.
    
    Args:
        message_id: Message ID to delete
        current_user: Authenticated user (must be sender)
        db: Database session
    """
    try:
        from src.models.message import Message
        
        # Get message
        message = db.query(Message).filter(
            Message.message_id == message_id
        ).first()
        
        if not message:
            raise create_error_response(
                message="Message not found",
                error_code="MESSAGE_NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        # Verify user is the sender
        if message.sender_id != current_user.user_id:
            raise create_error_response(
                message="Only the sender can delete this message",
                error_code="UNAUTHORIZED_ACTION",
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        # Delete message
        db.delete(message)
        db.commit()
        
        logger.info(f"Message deleted: {message_id}")
        
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting message: {e}")
        raise create_error_response(
            message=f"Failed to delete message: {str(e)}",
            error_code="MESSAGE_DELETE_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ============================================================================
# MESSAGING SYSTEM ENDPOINTS
# ============================================================================

class MessageCreate(BaseModel):
    """Request model for creating a message."""
    connection_id: str = Field(..., description="ID of the connection")
    content: str = Field(..., min_length=1, max_length=2000, description="Message content")


class MessageResponse(BaseModel):
    """Response model for a message."""
    message_id: str
    connection_id: str
    sender_id: str
    receiver_id: str
    content: str
    is_read: bool
    created_at: str
    sender_info: Optional[dict] = None


@app.post(
    "/api/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Send a message",
    description="Send a message to a connected user"
)
async def send_message(
    message_data: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Send a message to a connected user.
    
    Args:
        message_data: Message content and connection ID
        current_user: Authenticated user (sender)
        db: Database session
        
    Returns:
        Created message with sender information
    """
    try:
        from src.models.connection import Connection
        from src.models.message import Message
        
        # Verify connection exists and user is part of it
        connection = db.query(Connection).filter(
            Connection.connection_id == message_data.connection_id
        ).first()
        
        if not connection:
            raise create_error_response(
                message="Connection not found",
                error_code="CONNECTION_NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        # Verify connection is accepted
        if connection.status != 'accepted':
            raise create_error_response(
                message="Can only message accepted connections",
                error_code="CONNECTION_NOT_ACCEPTED",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        # Determine sender and receiver
        if connection.requester_id == current_user.user_id:
            receiver_id = connection.helper_id
        elif connection.helper_id == current_user.user_id:
            receiver_id = connection.requester_id
        else:
            raise create_error_response(
                message="You are not part of this connection",
                error_code="UNAUTHORIZED_CONNECTION",
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        # Create message
        message_id = f"msg_{datetime.now().strftime('%Y%m%d%H%M%S')}_{current_user.user_id[:8]}"
        
        new_message = Message(
            message_id=message_id,
            connection_id=message_data.connection_id,
            sender_id=current_user.user_id,
            receiver_id=receiver_id,
            content=message_data.content,
            is_read=False
        )
        
        db.add(new_message)
        db.commit()
        db.refresh(new_message)
        
        logger.info(f"Message sent: {message_id}")
        
        # Prepare response
        response = MessageResponse(
            message_id=new_message.message_id,
            connection_id=new_message.connection_id,
            sender_id=new_message.sender_id,
            receiver_id=new_message.receiver_id,
            content=new_message.content,
            is_read=new_message.is_read,
            created_at=new_message.created_at.isoformat(),
            sender_info={
                'user_id': current_user.user_id,
                'full_name': current_user.full_name
            }
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        logger.error(traceback.format_exc())
        raise create_error_response(
            message=f"Failed to send message: {str(e)}",
            error_code="MESSAGE_SEND_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@app.get(
    "/api/messages/conversation/{connection_id}",
    summary="Get conversation messages",
    description="Get all messages for a specific connection"
)
async def get_conversation(
    connection_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all messages for a connection.
    
    Args:
        connection_id: Connection ID
        current_user: Authenticated user
        db: Database session
        
    Returns:
        List of messages with user information
    """
    try:
        from src.models.connection import Connection
        from src.models.message import Message
        
        # Verify connection exists and user is part of it
        connection = db.query(Connection).filter(
            Connection.connection_id == connection_id
        ).first()
        
        if not connection:
            raise create_error_response(
                message="Connection not found",
                error_code="CONNECTION_NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        # Verify user is part of connection
        if connection.requester_id != current_user.user_id and connection.helper_id != current_user.user_id:
            raise create_error_response(
                message="You are not part of this connection",
                error_code="UNAUTHORIZED_CONNECTION",
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        # Get all messages for this connection
        messages = db.query(Message).filter(
            Message.connection_id == connection_id
        ).order_by(Message.created_at.asc()).all()
        
        # Mark messages as read if current user is receiver
        for msg in messages:
            if msg.receiver_id == current_user.user_id and not msg.is_read:
                msg.is_read = True
        
        db.commit()
        
        # Get other user info
        other_user_id = connection.helper_id if connection.requester_id == current_user.user_id else connection.requester_id
        other_user = db.query(User).filter(User.user_id == other_user_id).first()
        
        # Format messages
        message_list = []
        for msg in messages:
            sender = db.query(User).filter(User.user_id == msg.sender_id).first()
            message_list.append({
                'message_id': msg.message_id,
                'connection_id': msg.connection_id,
                'sender_id': msg.sender_id,
                'receiver_id': msg.receiver_id,
                'content': msg.content,
                'is_read': msg.is_read,
                'created_at': msg.created_at.isoformat(),
                'is_mine': msg.sender_id == current_user.user_id,
                'sender_name': sender.full_name if sender else 'Unknown'
            })
        
        return {
            'connection_id': connection_id,
            'messages': message_list,
            'other_user': {
                'user_id': other_user.user_id,
                'full_name': other_user.full_name,
                'user_type': other_user.user_type
            } if other_user else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving conversation: {e}")
        raise create_error_response(
            message=f"Failed to retrieve conversation: {str(e)}",
            error_code="CONVERSATION_RETRIEVAL_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@app.get(
    "/api/messages/conversations",
    summary="Get all conversations",
    description="Get list of all conversations for current user"
)
async def get_conversations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all conversations for the current user.
    
    Args:
        current_user: Authenticated user
        db: Database session
        
    Returns:
        List of conversations with last message and unread count
    """
    try:
        from src.models.connection import Connection
        from src.models.message import Message
        
        # Get all accepted connections for user
        connections = db.query(Connection).filter(
            ((Connection.requester_id == current_user.user_id) | 
             (Connection.helper_id == current_user.user_id)),
            Connection.status == 'accepted'
        ).all()
        
        conversations = []
        
        for conn in connections:
            # Get other user
            other_user_id = conn.helper_id if conn.requester_id == current_user.user_id else conn.requester_id
            other_user = db.query(User).filter(User.user_id == other_user_id).first()
            
            # Get last message
            last_message = db.query(Message).filter(
                Message.connection_id == conn.connection_id
            ).order_by(Message.created_at.desc()).first()
            
            # Count unread messages
            unread_count = db.query(Message).filter(
                Message.connection_id == conn.connection_id,
                Message.receiver_id == current_user.user_id,
                Message.is_read == False
            ).count()
            
            conversations.append({
                'connection_id': conn.connection_id,
                'other_user': {
                    'user_id': other_user.user_id,
                    'full_name': other_user.full_name,
                    'user_type': other_user.user_type,
                    'city': other_user.city,
                    'state': other_user.state
                } if other_user else None,
                'last_message': {
                    'content': last_message.content,
                    'created_at': last_message.created_at.isoformat(),
                    'is_mine': last_message.sender_id == current_user.user_id
                } if last_message else None,
                'unread_count': unread_count,
                'created_at': conn.created_at.isoformat()
            })
        
        # Sort by last message time (most recent first)
        conversations.sort(key=lambda x: x['last_message']['created_at'] if x['last_message'] else x['created_at'], reverse=True)
        
        return {'conversations': conversations, 'count': len(conversations)}
        
    except Exception as e:
        logger.error(f"Error retrieving conversations: {e}")
        raise create_error_response(
            message=f"Failed to retrieve conversations: {str(e)}",
            error_code="CONVERSATIONS_RETRIEVAL_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@app.get(
    "/api/messages/unread",
    summary="Get unread message count",
    description="Get total count of unread messages"
)
async def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get unread message count for current user.
    
    Args:
        current_user: Authenticated user
        db: Database session
        
    Returns:
        Unread message count
    """
    try:
        from src.models.message import Message
        
        unread_count = db.query(Message).filter(
            Message.receiver_id == current_user.user_id,
            Message.is_read == False
        ).count()
        
        return {'unread_count': unread_count}
        
    except Exception as e:
        logger.error(f"Error getting unread count: {e}")
        raise create_error_response(
            message=f"Failed to get unread count: {str(e)}",
            error_code="UNREAD_COUNT_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@app.delete(
    "/api/messages/{message_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a message",
    description="Delete a message (sender only)"
)
async def delete_message(
    message_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a message.
    
    Args:
        message_id: Message ID to delete
        current_user: Authenticated user (must be sender)
        db: Database session
    """
    try:
        from src.models.message import Message
        
        # Get message
        message = db.query(Message).filter(
            Message.message_id == message_id
        ).first()
        
        if not message:
            raise create_error_response(
                message="Message not found",
                error_code="MESSAGE_NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        # Verify user is sender
        if message.sender_id != current_user.user_id:
            raise create_error_response(
                message="Only the sender can delete this message",
                error_code="UNAUTHORIZED_ACTION",
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        # Delete message
        db.delete(message)
        db.commit()
        
        logger.info(f"Message deleted: {message_id}")
        
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting message: {e}")
        raise create_error_response(
            message=f"Failed to delete message: {str(e)}",
            error_code="MESSAGE_DELETE_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ============================================================================
# MESSAGING SYSTEM ENDPOINTS
# ============================================================================

class MessageCreate(BaseModel):
    """Request model for creating a message."""
    connection_id: str = Field(..., description="ID of the connection")
    content: str = Field(..., min_length=1, max_length=2000, description="Message content")


class MessageResponse(BaseModel):
    """Response model for a message."""
    message_id: str
    connection_id: str
    sender_id: str
    receiver_id: str
    content: str
    is_read: bool
    created_at: str
    sender_info: Optional[dict] = None


@app.post(
    "/api/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Send a message",
    description="Send a message to a connected user"
)
async def send_message(
    message_data: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Send a message to a connected user.
    
    Args:
        message_data: Message content and connection ID
        current_user: Authenticated user (sender)
        db: Database session
        
    Returns:
        Created message with sender information
    """
    try:
        from src.models.connection import Connection
        from src.models.message import Message
        
        # Verify connection exists and user is part of it
        connection = db.query(Connection).filter(
            Connection.connection_id == message_data.connection_id
        ).first()
        
        if not connection:
            raise create_error_response(
                message="Connection not found",
                error_code="CONNECTION_NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        # Verify connection is accepted
        if connection.status != 'accepted':
            raise create_error_response(
                message="Can only message accepted connections",
                error_code="CONNECTION_NOT_ACCEPTED",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        # Verify user is part of the connection
        if current_user.user_id not in [connection.requester_id, connection.helper_id]:
            raise create_error_response(
                message="You are not part of this connection",
                error_code="UNAUTHORIZED_CONNECTION",
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        # Determine receiver
        receiver_id = connection.helper_id if current_user.user_id == connection.requester_id else connection.requester_id
        
        # Create message
        message_id = f"msg_{datetime.now().strftime('%Y%m%d%H%M%S')}_{current_user.user_id[:8]}"
        
        new_message = Message(
            message_id=message_id,
            connection_id=message_data.connection_id,
            sender_id=current_user.user_id,
            receiver_id=receiver_id,
            content=message_data.content,
            is_read=False
        )
        
        db.add(new_message)
        db.commit()
        db.refresh(new_message)
        
        logger.info(f"Message sent: {message_id}")
        
        # Prepare response
        response = MessageResponse(
            message_id=new_message.message_id,
            connection_id=new_message.connection_id,
            sender_id=new_message.sender_id,
            receiver_id=new_message.receiver_id,
            content=new_message.content,
            is_read=new_message.is_read,
            created_at=new_message.created_at.isoformat(),
            sender_info={
                'user_id': current_user.user_id,
                'full_name': current_user.full_name
            }
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        logger.error(traceback.format_exc())
        raise create_error_response(
            message=f"Failed to send message: {str(e)}",
            error_code="MESSAGE_SEND_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@app.get(
    "/api/messages/conversation/{connection_id}",
    summary="Get conversation messages",
    description="Get all messages for a specific connection"
)
async def get_conversation(
    connection_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all messages for a connection.
    
    Args:
        connection_id: Connection ID
        current_user: Authenticated user
        db: Database session
        
    Returns:
        List of messages with user information
    """
    try:
        from src.models.connection import Connection
        from src.models.message import Message
        
        # Verify connection exists and user is part of it
        connection = db.query(Connection).filter(
            Connection.connection_id == connection_id
        ).first()
        
        if not connection:
            raise create_error_response(
                message="Connection not found",
                error_code="CONNECTION_NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        # Verify user is part of the connection
        if current_user.user_id not in [connection.requester_id, connection.helper_id]:
            raise create_error_response(
                message="You are not part of this connection",
                error_code="UNAUTHORIZED_CONNECTION",
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        # Get all messages for this connection
        messages = db.query(Message).filter(
            Message.connection_id == connection_id
        ).order_by(Message.created_at.asc()).all()
        
        # Mark messages as read if current user is receiver
        for msg in messages:
            if msg.receiver_id == current_user.user_id and not msg.is_read:
                msg.is_read = True
        
        db.commit()
        
        # Get other user info
        other_user_id = connection.helper_id if current_user.user_id == connection.requester_id else connection.requester_id
        other_user = db.query(User).filter(User.user_id == other_user_id).first()
        
        # Format messages
        message_list = []
        for msg in messages:
            sender = db.query(User).filter(User.user_id == msg.sender_id).first()
            message_list.append({
                'message_id': msg.message_id,
                'connection_id': msg.connection_id,
                'sender_id': msg.sender_id,
                'receiver_id': msg.receiver_id,
                'content': msg.content,
                'is_read': msg.is_read,
                'created_at': msg.created_at.isoformat(),
                'is_mine': msg.sender_id == current_user.user_id,
                'sender_name': sender.full_name if sender else 'Unknown'
            })
        
        return {
            'connection_id': connection_id,
            'messages': message_list,
            'other_user': {
                'user_id': other_user.user_id,
                'full_name': other_user.full_name,
                'user_type': other_user.user_type
            } if other_user else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving conversation: {e}")
        raise create_error_response(
            message=f"Failed to retrieve conversation: {str(e)}",
            error_code="CONVERSATION_RETRIEVAL_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@app.get(
    "/api/messages/conversations",
    summary="Get all conversations",
    description="Get list of all conversations for current user"
)
async def get_conversations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all conversations for the current user.
    
    Args:
        current_user: Authenticated user
        db: Database session
        
    Returns:
        List of conversations with last message and unread count
    """
    try:
        from src.models.connection import Connection
        from src.models.message import Message
        
        # Get all accepted connections for user
        connections = db.query(Connection).filter(
            ((Connection.requester_id == current_user.user_id) | 
             (Connection.helper_id == current_user.user_id)),
            Connection.status == 'accepted'
        ).all()
        
        conversations = []
        
        for conn in connections:
            # Get other user
            other_user_id = conn.helper_id if current_user.user_id == conn.requester_id else conn.requester_id
            other_user = db.query(User).filter(User.user_id == other_user_id).first()
            
            # Get last message
            last_message = db.query(Message).filter(
                Message.connection_id == conn.connection_id
            ).order_by(Message.created_at.desc()).first()
            
            # Count unread messages
            unread_count = db.query(Message).filter(
                Message.connection_id == conn.connection_id,
                Message.receiver_id == current_user.user_id,
                Message.is_read == False
            ).count()
            
            conversations.append({
                'connection_id': conn.connection_id,
                'other_user': {
                    'user_id': other_user.user_id,
                    'full_name': other_user.full_name,
                    'user_type': other_user.user_type,
                    'city': other_user.city,
                    'state': other_user.state
                } if other_user else None,
                'last_message': {
                    'content': last_message.content,
                    'created_at': last_message.created_at.isoformat(),
                    'is_mine': last_message.sender_id == current_user.user_id
                } if last_message else None,
                'unread_count': unread_count,
                'created_at': conn.created_at.isoformat()
            })
        
        # Sort by last message time (most recent first)
        conversations.sort(key=lambda x: x['last_message']['created_at'] if x['last_message'] else x['created_at'], reverse=True)
        
        return {'conversations': conversations, 'count': len(conversations)}
        
    except Exception as e:
        logger.error(f"Error retrieving conversations: {e}")
        raise create_error_response(
            message=f"Failed to retrieve conversations: {str(e)}",
            error_code="CONVERSATIONS_RETRIEVAL_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@app.get(
    "/api/messages/unread",
    summary="Get unread message count",
    description="Get total count of unread messages"
)
async def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get unread message count for current user.
    
    Args:
        current_user: Authenticated user
        db: Database session
        
    Returns:
        Unread message count
    """
    try:
        from src.models.message import Message
        
        unread_count = db.query(Message).filter(
            Message.receiver_id == current_user.user_id,
            Message.is_read == False
        ).count()
        
        return {'unread_count': unread_count}
        
    except Exception as e:
        logger.error(f"Error getting unread count: {e}")
        raise create_error_response(
            message=f"Failed to get unread count: {str(e)}",
            error_code="UNREAD_COUNT_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@app.delete(
    "/api/messages/{message_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a message",
    description="Delete a message (sender only)"
)
async def delete_message(
    message_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a message.
    
    Args:
        message_id: Message ID to delete
        current_user: Authenticated user (must be sender)
        db: Database session
    """
    try:
        from src.models.message import Message
        
        # Get message
        message = db.query(Message).filter(
            Message.message_id == message_id
        ).first()
        
        if not message:
            raise create_error_response(
                message="Message not found",
                error_code="MESSAGE_NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        # Verify user is the sender
        if message.sender_id != current_user.user_id:
            raise create_error_response(
                message="Only the sender can delete this message",
                error_code="UNAUTHORIZED_ACTION",
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        # Delete message
        db.delete(message)
        db.commit()
        
        logger.info(f"Message deleted: {message_id}")
        
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting message: {e}")
        raise create_error_response(
            message=f"Failed to delete message: {str(e)}",
            error_code="MESSAGE_DELETE_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ============================================================================
# MESSAGING SYSTEM ENDPOINTS
# ============================================================================

class MessageCreate(BaseModel):
    """Request model for creating a message."""
    connection_id: str = Field(..., description="ID of the connection")
    content: str = Field(..., min_length=1, max_length=2000, description="Message content")


class MessageResponse(BaseModel):
    """Response model for a message."""
    message_id: str
    connection_id: str
    sender_id: str
    receiver_id: str
    content: str
    is_read: bool
    created_at: str
    sender_info: Optional[dict] = None


@app.post(
    "/api/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Send a message",
    description="Send a message to a connected user"
)
async def send_message(
    message_data: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Send a message to a connected user.
    
    Args:
        message_data: Message content and connection ID
        current_user: Authenticated user (sender)
        db: Database session
        
    Returns:
        Created message with sender information
    """
    try:
        from src.models.connection import Connection
        from src.models.message import Message
        
        # Verify connection exists and user is part of it
        connection = db.query(Connection).filter(
            Connection.connection_id == message_data.connection_id
        ).first()
        
        if not connection:
            raise create_error_response(
                message="Connection not found",
                error_code="CONNECTION_NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        # Verify connection is accepted
        if connection.status != 'accepted':
            raise create_error_response(
                message="Can only message accepted connections",
                error_code="CONNECTION_NOT_ACCEPTED",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        # Verify user is part of the connection
        if current_user.user_id not in [connection.requester_id, connection.helper_id]:
            raise create_error_response(
                message="You are not part of this connection",
                error_code="UNAUTHORIZED_CONNECTION",
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        # Determine receiver
        receiver_id = connection.helper_id if current_user.user_id == connection.requester_id else connection.requester_id
        
        # Create message
        message_id = f"msg_{datetime.now().strftime('%Y%m%d%H%M%S')}_{current_user.user_id[:8]}"
        
        new_message = Message(
            message_id=message_id,
            connection_id=message_data.connection_id,
            sender_id=current_user.user_id,
            receiver_id=receiver_id,
            content=message_data.content,
            is_read=False
        )
        
        db.add(new_message)
        db.commit()
        db.refresh(new_message)
        
        logger.info(f"Message sent: {message_id}")
        
        # Prepare response
        response = MessageResponse(
            message_id=new_message.message_id,
            connection_id=new_message.connection_id,
            sender_id=new_message.sender_id,
            receiver_id=new_message.receiver_id,
            content=new_message.content,
            is_read=new_message.is_read,
            created_at=new_message.created_at.isoformat(),
            sender_info={
                'user_id': current_user.user_id,
                'full_name': current_user.full_name
            }
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        logger.error(traceback.format_exc())
        raise create_error_response(
            message=f"Failed to send message: {str(e)}",
            error_code="MESSAGE_SEND_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@app.get(
    "/api/messages/conversation/{connection_id}",
    summary="Get conversation messages",
    description="Get all messages for a specific connection"
)
async def get_conversation(
    connection_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all messages for a connection.
    
    Args:
        connection_id: Connection ID
        current_user: Authenticated user
        db: Database session
        
    Returns:
        List of messages with user information
    """
    try:
        from src.models.connection import Connection
        from src.models.message import Message
        
        # Verify connection exists and user is part of it
        connection = db.query(Connection).filter(
            Connection.connection_id == connection_id
        ).first()
        
        if not connection:
            raise create_error_response(
                message="Connection not found",
                error_code="CONNECTION_NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        # Verify user is part of the connection
        if current_user.user_id not in [connection.requester_id, connection.helper_id]:
            raise create_error_response(
                message="You are not part of this connection",
                error_code="UNAUTHORIZED_CONNECTION",
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        # Get all messages for this connection
        messages = db.query(Message).filter(
            Message.connection_id == connection_id
        ).order_by(Message.created_at.asc()).all()
        
        # Mark messages as read if current user is receiver
        for msg in messages:
            if msg.receiver_id == current_user.user_id and not msg.is_read:
                msg.is_read = True
        
        db.commit()
        
        # Get other user info
        other_user_id = connection.helper_id if current_user.user_id == connection.requester_id else connection.requester_id
        other_user = db.query(User).filter(User.user_id == other_user_id).first()
        
        # Format messages
        message_list = []
        for msg in messages:
            sender = db.query(User).filter(User.user_id == msg.sender_id).first()
            message_list.append({
                'message_id': msg.message_id,
                'connection_id': msg.connection_id,
                'sender_id': msg.sender_id,
                'receiver_id': msg.receiver_id,
                'content': msg.content,
                'is_read': msg.is_read,
                'created_at': msg.created_at.isoformat(),
                'is_mine': msg.sender_id == current_user.user_id,
                'sender_name': sender.full_name if sender else 'Unknown'
            })
        
        return {
            'connection_id': connection_id,
            'messages': message_list,
            'other_user': {
                'user_id': other_user.user_id,
                'full_name': other_user.full_name,
                'user_type': other_user.user_type
            } if other_user else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving conversation: {e}")
        raise create_error_response(
            message=f"Failed to retrieve conversation: {str(e)}",
            error_code="CONVERSATION_RETRIEVAL_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@app.get(
    "/api/messages/conversations",
    summary="Get all conversations",
    description="Get list of all conversations for current user"
)
async def get_conversations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all conversations for the current user.
    
    Args:
        current_user: Authenticated user
        db: Database session
        
    Returns:
        List of conversations with last message and unread count
    """
    try:
        from src.models.connection import Connection
        from src.models.message import Message
        
        # Get all accepted connections for user
        connections = db.query(Connection).filter(
            ((Connection.requester_id == current_user.user_id) | 
             (Connection.helper_id == current_user.user_id)),
            Connection.status == 'accepted'
        ).all()
        
        conversations = []
        
        for conn in connections:
            # Get other user
            other_user_id = conn.helper_id if current_user.user_id == conn.requester_id else conn.requester_id
            other_user = db.query(User).filter(User.user_id == other_user_id).first()
            
            # Get last message
            last_message = db.query(Message).filter(
                Message.connection_id == conn.connection_id
            ).order_by(Message.created_at.desc()).first()
            
            # Count unread messages
            unread_count = db.query(Message).filter(
                Message.connection_id == conn.connection_id,
                Message.receiver_id == current_user.user_id,
                Message.is_read == False
            ).count()
            
            conversations.append({
                'connection_id': conn.connection_id,
                'other_user': {
                    'user_id': other_user.user_id,
                    'full_name': other_user.full_name,
                    'user_type': other_user.user_type,
                    'city': other_user.city,
                    'state': other_user.state
                } if other_user else None,
                'last_message': {
                    'content': last_message.content,
                    'created_at': last_message.created_at.isoformat(),
                    'is_mine': last_message.sender_id == current_user.user_id
                } if last_message else None,
                'unread_count': unread_count,
                'created_at': conn.created_at.isoformat()
            })
        
        # Sort by last message time (most recent first)
        conversations.sort(key=lambda x: x['last_message']['created_at'] if x['last_message'] else x['created_at'], reverse=True)
        
        return {'conversations': conversations, 'count': len(conversations)}
        
    except Exception as e:
        logger.error(f"Error retrieving conversations: {e}")
        raise create_error_response(
            message=f"Failed to retrieve conversations: {str(e)}",
            error_code="CONVERSATIONS_RETRIEVAL_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@app.get(
    "/api/messages/unread",
    summary="Get unread message count",
    description="Get total count of unread messages"
)
async def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get unread message count for current user.
    
    Args:
        current_user: Authenticated user
        db: Database session
        
    Returns:
        Unread message count
    """
    try:
        from src.models.message import Message
        
        unread_count = db.query(Message).filter(
            Message.receiver_id == current_user.user_id,
            Message.is_read == False
        ).count()
        
        return {'unread_count': unread_count}
        
    except Exception as e:
        logger.error(f"Error retrieving unread count: {e}")
        raise create_error_response(
            message=f"Failed to retrieve unread count: {str(e)}",
            error_code="UNREAD_COUNT_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@app.delete(
    "/api/messages/{message_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a message",
    description="Delete a message (sender only)"
)
async def delete_message(
    message_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a message.
    
    Args:
        message_id: Message ID to delete
        current_user: Authenticated user (must be sender)
        db: Database session
    """
    try:
        from src.models.message import Message
        
        # Get message
        message = db.query(Message).filter(
            Message.message_id == message_id
        ).first()
        
        if not message:
            raise create_error_response(
                message="Message not found",
                error_code="MESSAGE_NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        # Verify user is the sender
        if message.sender_id != current_user.user_id:
            raise create_error_response(
                message="Only the sender can delete this message",
                error_code="UNAUTHORIZED_ACTION",
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        # Delete message
        db.delete(message)
        db.commit()
        
        logger.info(f"Message deleted: {message_id}")
        
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting message: {e}")
        raise create_error_response(
            message=f"Failed to delete message: {str(e)}",
            error_code="MESSAGE_DELETE_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ============================================================================
# RATING & REVIEW SYSTEM ENDPOINTS
# ============================================================================

class RatingCreate(BaseModel):
    """Request model for creating a rating."""
    connection_id: str = Field(..., description="ID of the connection")
    rated_user_id: str = Field(..., description="ID of the user being rated")
    rating: float = Field(..., ge=0.0, le=5.0, description="Rating score (0-5)")
    review: Optional[str] = Field(None, max_length=1000, description="Optional review text")


class RatingResponse(BaseModel):
    """Response model for a rating."""
    rating_id: str
    connection_id: str
    rater_id: str
    rated_user_id: str
    rating: float
    review: Optional[str]
    created_at: str
    rater_info: Optional[dict] = None


@app.post(
    "/api/ratings",
    response_model=RatingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a rating",
    description="Rate a user after consultation"
)
async def create_rating(
    rating_data: RatingCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a rating for a user.
    
    Args:
        rating_data: Rating details
        current_user: Authenticated user (rater)
        db: Database session
        
    Returns:
        Created rating with rater information
    """
    try:
        from src.models.connection import Connection
        from src.models.rating import Rating
        
        # Verify connection exists and is accepted
        connection = db.query(Connection).filter(
            Connection.connection_id == rating_data.connection_id
        ).first()
        
        if not connection:
            raise create_error_response(
                message="Connection not found",
                error_code="CONNECTION_NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        if connection.status != 'accepted':
            raise create_error_response(
                message="Can only rate accepted connections",
                error_code="CONNECTION_NOT_ACCEPTED",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        # Verify user is part of the connection
        if current_user.user_id not in [connection.requester_id, connection.helper_id]:
            raise create_error_response(
                message="You are not part of this connection",
                error_code="UNAUTHORIZED_CONNECTION",
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        # Verify rated user is the other person in connection
        if rating_data.rated_user_id not in [connection.requester_id, connection.helper_id]:
            raise create_error_response(
                message="Can only rate users in this connection",
                error_code="INVALID_RATED_USER",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        if rating_data.rated_user_id == current_user.user_id:
            raise create_error_response(
                message="Cannot rate yourself",
                error_code="SELF_RATING",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if already rated
        existing_rating = db.query(Rating).filter(
            Rating.connection_id == rating_data.connection_id,
            Rating.rater_id == current_user.user_id
        ).first()
        
        if existing_rating:
            raise create_error_response(
                message="You have already rated this user for this connection",
                error_code="DUPLICATE_RATING",
                status_code=status.HTTP_409_CONFLICT
            )
        
        # Create rating
        rating_id = f"rating_{datetime.now().strftime('%Y%m%d%H%M%S')}_{current_user.user_id[:8]}"
        
        new_rating = Rating(
            rating_id=rating_id,
            connection_id=rating_data.connection_id,
            rater_id=current_user.user_id,
            rated_user_id=rating_data.rated_user_id,
            rating=rating_data.rating,
            review=rating_data.review
        )
        
        db.add(new_rating)
        
        # Update rated user's reputation
        rated_user = db.query(User).filter(User.user_id == rating_data.rated_user_id).first()
        if rated_user:
            # Calculate new reputation score
            all_ratings = db.query(Rating).filter(
                Rating.rated_user_id == rating_data.rated_user_id
            ).all()
            
            total_ratings = len(all_ratings) + 1  # Include new rating
            total_score = sum(r.rating for r in all_ratings) + rating_data.rating
            new_reputation = total_score / total_ratings
            
            rated_user.reputation_score = new_reputation
            rated_user.total_ratings = total_ratings
        
        db.commit()
        db.refresh(new_rating)
        
        logger.info(f"Rating created: {rating_id}")
        
        # Prepare response
        response = RatingResponse(
            rating_id=new_rating.rating_id,
            connection_id=new_rating.connection_id,
            rater_id=new_rating.rater_id,
            rated_user_id=new_rating.rated_user_id,
            rating=new_rating.rating,
            review=new_rating.review,
            created_at=new_rating.created_at.isoformat(),
            rater_info={
                'user_id': current_user.user_id,
                'full_name': current_user.full_name
            }
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating rating: {e}")
        logger.error(traceback.format_exc())
        raise create_error_response(
            message=f"Failed to create rating: {str(e)}",
            error_code="RATING_CREATE_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@app.get(
    "/api/ratings/user/{user_id}",
    summary="Get user ratings",
    description="Get all ratings for a specific user"
)
async def get_user_ratings(
    user_id: str,
    db: Session = Depends(get_db)
):
    """
    Get all ratings for a user.
    
    Args:
        user_id: User ID to get ratings for
        db: Database session
        
    Returns:
        List of ratings with rater information
    """
    try:
        from src.models.rating import Rating
        
        # Get user
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            raise create_error_response(
                message="User not found",
                error_code="USER_NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        # Get all ratings
        ratings = db.query(Rating).filter(
            Rating.rated_user_id == user_id
        ).order_by(Rating.created_at.desc()).all()
        
        # Format ratings with rater info
        rating_list = []
        for rating in ratings:
            rater = db.query(User).filter(User.user_id == rating.rater_id).first()
            rating_list.append({
                'rating_id': rating.rating_id,
                'rating': rating.rating,
                'review': rating.review,
                'created_at': rating.created_at.isoformat(),
                'rater': {
                    'user_id': rater.user_id,
                    'full_name': rater.full_name,
                    'user_type': rater.user_type
                } if rater else None
            })
        
        return {
            'user_id': user_id,
            'ratings': rating_list,
            'count': len(rating_list),
            'average_rating': user.reputation_score,
            'total_ratings': user.total_ratings
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving ratings: {e}")
        raise create_error_response(
            message=f"Failed to retrieve ratings: {str(e)}",
            error_code="RATINGS_RETRIEVAL_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@app.get(
    "/api/ratings/connection/{connection_id}",
    summary="Get ratings for connection",
    description="Get ratings given for a specific connection"
)
async def get_connection_ratings(
    connection_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get ratings for a specific connection.
    
    Args:
        connection_id: Connection ID
        current_user: Authenticated user
        db: Database session
        
    Returns:
        Ratings for the connection
    """
    try:
        from src.models.connection import Connection
        from src.models.rating import Rating
        
        # Verify connection exists and user is part of it
        connection = db.query(Connection).filter(
            Connection.connection_id == connection_id
        ).first()
        
        if not connection:
            raise create_error_response(
                message="Connection not found",
                error_code="CONNECTION_NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        if current_user.user_id not in [connection.requester_id, connection.helper_id]:
            raise create_error_response(
                message="You are not part of this connection",
                error_code="UNAUTHORIZED_CONNECTION",
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        # Get ratings for this connection
        ratings = db.query(Rating).filter(
            Rating.connection_id == connection_id
        ).all()
        
        # Check if current user has rated
        user_rating = next((r for r in ratings if r.rater_id == current_user.user_id), None)
        other_rating = next((r for r in ratings if r.rater_id != current_user.user_id), None)
        
        return {
            'connection_id': connection_id,
            'user_has_rated': user_rating is not None,
            'user_rating': {
                'rating': user_rating.rating,
                'review': user_rating.review,
                'created_at': user_rating.created_at.isoformat()
            } if user_rating else None,
            'received_rating': {
                'rating': other_rating.rating,
                'review': other_rating.review,
                'created_at': other_rating.created_at.isoformat()
            } if other_rating else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving connection ratings: {e}")
        raise create_error_response(
            message=f"Failed to retrieve ratings: {str(e)}",
            error_code="CONNECTION_RATINGS_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@app.get(
    "/api/ratings/stats/{user_id}",
    summary="Get rating statistics",
    description="Get detailed rating statistics for a user"
)
async def get_rating_stats(
    user_id: str,
    db: Session = Depends(get_db)
):
    """
    Get rating statistics for a user.
    
    Args:
        user_id: User ID
        db: Database session
        
    Returns:
        Rating statistics including distribution
    """
    try:
        from src.models.rating import Rating
        
        # Get user
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            raise create_error_response(
                message="User not found",
                error_code="USER_NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        # Get all ratings
        ratings = db.query(Rating).filter(
            Rating.rated_user_id == user_id
        ).all()
        
        if not ratings:
            return {
                'user_id': user_id,
                'average_rating': 0.0,
                'total_ratings': 0,
                'distribution': {5: 0, 4: 0, 3: 0, 2: 0, 1: 0},
                'percentage_positive': 0.0
            }
        
        # Calculate distribution
        distribution = {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
        for rating in ratings:
            rounded = round(rating.rating)
            if rounded in distribution:
                distribution[rounded] += 1
        
        # Calculate percentage positive (4+ stars)
        positive = distribution[5] + distribution[4]
        percentage_positive = (positive / len(ratings)) * 100 if ratings else 0
        
        return {
            'user_id': user_id,
            'average_rating': user.reputation_score,
            'total_ratings': len(ratings),
            'distribution': distribution,
            'percentage_positive': round(percentage_positive, 1)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving rating stats: {e}")
        raise create_error_response(
            message=f"Failed to retrieve rating statistics: {str(e)}",
            error_code="RATING_STATS_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
