#!/usr/bin/env python3
"""Fixed RAG-MCP Server with proper SSE handling"""

import os
import sys
import argparse
import asyncio
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import Response, StreamingResponse
from starlette.routing import Route
import uvicorn

from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp_instance import mcp
from src.config import get_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import tools
from tools import tool_rag_orchestrator_sse  # This imports and registers all tools

def create_sse_app(mcp_server: Server, *, debug: bool = False) -> Starlette:
    """Create a Starlette application with fixed SSE handling."""
    
    # Create SSE transport
    sse_transport = SseServerTransport("/messages/")
    
    async def handle_sse(request: Request):
        """Handle SSE connection"""
        logger.info("SSE connection request received")
        async with sse_transport.connect_sse(
            request.scope,
            request.receive,
            request._send,
        ) as (read_stream, write_stream):
            await mcp_server.run(
                read_stream,
                write_stream,
                mcp_server.create_initialization_options(),
            )
    
    async def handle_messages(request: Request):
        """Handle POST to /messages/ endpoint"""
        logger.info(f"Message POST request received: {request.url}")
        
        # Get the session_id from query params
        session_id = request.query_params.get("session_id")
        if not session_id:
            return Response("Missing session_id", status_code=400)
        
        # Read the request body
        body = await request.body()
        
        # Use the SSE transport's internal message handler
        # This is a workaround for the TypeError
        try:
            # The SSE transport expects to handle this internally
            # We need to create a proper ASGI scope for it
            scope = request.scope.copy()
            
            # Create a receive callable that returns the body
            async def receive():
                return {
                    "type": "http.request",
                    "body": body,
                    "more_body": False,
                }
            
            # Create a send callable that captures the response
            response_started = False
            response_body = []
            
            async def send(message):
                nonlocal response_started
                if message["type"] == "http.response.start":
                    response_started = True
                elif message["type"] == "http.response.body":
                    response_body.append(message.get("body", b""))
            
            # Call the SSE transport's handle_post_message
            await sse_transport.handle_post_message(scope, receive, send)
            
            # Return the response
            if response_body:
                return Response(b"".join(response_body))
            else:
                return Response("OK")
                
        except Exception as e:
            logger.error(f"Error handling message: {e}", exc_info=True)
            return Response(f"Error: {str(e)}", status_code=500)
    
    # Create the Starlette app with proper routes
    app = Starlette(
        routes=[
            Route("/sse", endpoint=handle_sse, methods=["GET"]),
            Route("/messages/", endpoint=handle_messages, methods=["POST"]),
        ],
        debug=debug
    )
    
    return app

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Fixed RAG-MCP Server")
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
    
    logger.info(f"Starting Fixed RAG-MCP Server on {host}:{port}")
    logger.info(f"Model-MCP URL: {config.model_mcp_url}")
    logger.info(f"DB-MCP URL: {config.db_mcp_url}")
    
    # Get the MCP server instance
    mcp_server = mcp._mcp_server
    
    # Create SSE app
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