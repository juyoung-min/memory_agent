#!/usr/bin/env python3
"""RAG-MCP Server - Orchestrates Model-MCP and DB-MCP for RAG operations"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Add the current directory to the path
sys.path.insert(0, str(Path(__file__).parent))

from mcp_instance import mcp
from mcp.server.sse import SseServerTransport
from mcp.server import Server
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import StreamingResponse, Response, JSONResponse
from starlette.routing import Mount, Route
import uvicorn
import json

from src.config import get_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import tools
from tools import tool_rag_orchestrator  # This imports and registers all tools

def create_sse_app(mcp_server: Server, *, debug: bool = False) -> Starlette:
    """Create a Starlette application that can serve the provided mcp server with SSE."""
    # Create SSE transport with correct path
    sse = SseServerTransport("/messages/")
    
    async def handle_sse(request: Request):
        """Handle SSE connection"""
        logger.info("SSE connection request received")
        async with sse.connect_sse(
            request.scope,
            request.receive,
            request._send,
        ) as (read_stream, write_stream):
            await mcp_server.run(
                read_stream,
                write_stream,
                mcp_server.create_initialization_options(),
            )
    
    # The SSE transport expects to handle messages via its own internal mechanism
    # We'll use Starlette's mount to properly delegate
    sse_app = Starlette(
        routes=[
            Route("/sse", endpoint=handle_sse, methods=["GET"]),
            Mount("/messages", app=sse),  # Mount the SSE transport as an ASGI app
        ],
        debug=debug
    )
    
    return sse_app

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="RAG-MCP Server")
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
    
    logger.info(f"Starting RAG-MCP Server on {host}:{port}")
    logger.info(f"Model-MCP URL: {config.model_mcp_url}")
    logger.info(f"DB-MCP URL: {config.db_mcp_url}")
    
    # Get MCP server instance
    mcp_server = mcp._mcp_server
    
    # Create SSE app using MCP's built-in method
    app = create_sse_app(mcp_server, debug=args.log_level == "DEBUG")
    
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