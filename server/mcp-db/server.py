#!/usr/bin/env python3
"""DB-MCP Server - Pure database operations without embedding logic"""

import argparse
import asyncio
import logging
import sys
import os
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

from src.database.connection import create_pool, close_pool

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import tools
from tools import tool_db_core  # This imports and registers all tools

async def startup():
    """Initialize database connection pool on startup"""
    try:
        await create_pool()
        logger.info("Database connection pool initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database pool: {e}")
        raise

async def shutdown():
    """Close database connection pool on shutdown"""
    try:
        await close_pool()
        logger.info("Database connection pool closed")
    except Exception as e:
        logger.error(f"Error closing database pool: {e}")

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
    
    async def handle_health(request: Request):
        """Health check endpoint"""
        try:
            # Test database connection
            pool = await create_pool()
            async with pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            
            return JSONResponse({"status": "healthy", "service": "db-mcp"})
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return JSONResponse({"status": "unhealthy", "error": str(e)}, status_code=503)
    
    # The SSE transport expects to handle messages via its own internal mechanism
    # We'll use Starlette's mount to properly delegate
    sse_app = Starlette(
        routes=[
            Route("/sse", endpoint=handle_sse, methods=["GET"]),
            Mount("/messages", app=sse),  # Mount the SSE transport as an ASGI app
            Route("/health", endpoint=handle_health, methods=["GET"]),
        ],
        on_startup=[startup],
        on_shutdown=[shutdown],
        debug=debug
    )
    
    return sse_app


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="DB-MCP Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8092, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    parser.add_argument("--log-level", default="INFO", 
                       choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                       help="Set the logging level")
    
    args = parser.parse_args()
    
    # Update logging level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    # Get configuration from environment
    host = args.host or os.getenv("DB_HOST_BIND", "0.0.0.0")
    port = args.port or int(os.getenv("DB_PORT_BIND", "8092"))
    
    logger.info(f"Starting DB-MCP Server on {host}:{port}")
    logger.info(f"Database: {os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '5432')}/{os.getenv('DB_NAME', 'vector_db')}")
    
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