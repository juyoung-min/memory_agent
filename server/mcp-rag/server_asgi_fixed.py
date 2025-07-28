#!/usr/bin/env python3
"""RAG-MCP Server with ASGI-fixed SSE support"""

import os
import sys
import argparse
import logging
from pathlib import Path

# Add parent directory to path to import sse_asgi_fix
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

import uvicorn
from mcp_instance import mcp
from src.config import get_config
from sse_asgi_fix import create_sse_asgi_app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import tools to register them
from tools import tool_rag_orchestrator_sse

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="RAG-MCP Server with ASGI Fix")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8093, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    parser.add_argument("--log-level", default="INFO", 
                       choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                       help="Set the logging level")
    
    args = parser.parse_args()
    
    # Update logging level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    # Get configuration
    config = get_config()
    
    # Override with command line args if provided
    host = args.host or config.host
    port = args.port or config.port
    
    logger.info(f"Starting RAG-MCP Server (ASGI Fixed) on {host}:{port}")
    logger.info(f"Model-MCP URL: {config.model_mcp_url}")
    logger.info(f"DB-MCP URL: {config.db_mcp_url}")
    
    # Get the MCP server instance
    mcp_server = mcp._mcp_server
    
    # Create ASGI-compatible SSE app
    app = create_sse_asgi_app(mcp_server, debug=args.log_level == "DEBUG")
    
    # Run the server
    uvicorn.run(
        app,
        host=host,
        port=port,
        reload=args.reload,
        log_level=args.log_level.lower()
    )

if __name__ == "__main__":
    main()