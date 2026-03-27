#!/usr/bin/env python3
"""
Production Uvicorn server configuration for Legal Case Similarity API

This script provides production-ready configuration for running the FastAPI
application with Uvicorn in production environments.

Usage:
    python uvicorn_production.py

Environment Variables:
    HOST: Server bind address (default: 0.0.0.0)
    PORT: Server port (default: 8000)
    WORKERS: Number of worker processes (default: 4)
    LOG_LEVEL: Logging level (default: warning)
    ACCESS_LOG: Enable access logging (default: false)
"""

import os
import sys
import multiprocessing
from pathlib import Path

# Add src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))


def get_workers():
    """
    Calculate optimal number of workers based on CPU cores.
    
    Formula: (2 × CPU cores) + 1
    This provides good balance between concurrency and resource usage.
    
    Returns:
        int: Number of worker processes
    """
    cpu_count = multiprocessing.cpu_count()
    workers = (2 * cpu_count) + 1
    
    # Cap at 8 workers to prevent excessive resource usage
    return min(workers, 8)


def main():
    """Start the FastAPI application in production mode."""
    
    # Production configuration
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    # Default to 1 worker on free-tier hosting (512MB RAM) to avoid OOM crashes.
    # Each worker loads the full ML model into memory. Set WORKERS env var to increase.
    workers = int(os.getenv("WORKERS", "1"))
    log_level = os.getenv("LOG_LEVEL", "warning")
    access_log = os.getenv("ACCESS_LOG", "false").lower() == "true"
    
    print("=" * 60)
    print("Legal Case Similarity API - Production Mode")
    print("=" * 60)
    print(f"Host: {host}")
    print(f"Port: {port}")
    print(f"Workers: {workers}")
    print(f"Log Level: {log_level}")
    print(f"Access Log: {access_log}")
    print(f"CPU Cores: {multiprocessing.cpu_count()}")
    print("=" * 60)
    print("\nStarting server...")
    
    # Import uvicorn here to ensure proper path setup
    import uvicorn
    
    # Start the server with production configuration
    uvicorn.run(
        "api.main:app",
        host=host,
        port=port,
        workers=workers,
        log_level=log_level,
        access_log=access_log,
        proxy_headers=True,
        forwarded_allow_ips="*",
        timeout_keep_alive=5,
        limit_concurrency=100,
        limit_max_requests=1000,
        backlog=2048
    )


if __name__ == "__main__":
    main()
