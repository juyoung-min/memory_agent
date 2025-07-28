"""
Memory Agent MCP Server
Provides memory management with intelligent orchestration
"""

import asyncio
import logging
from typing import Optional
from starlette.applications import Starlette
from starlette.routing import Route
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import after logging is configured
from sse_transport import create_sse_transport
from mcp_instance import mcp

# Import tools
from tools import tool_memory_orchestrator_sse

async def health_check(request):
    """Health check endpoint"""
    from starlette.responses import JSONResponse
    return JSONResponse({"status": "healthy", "service": "memory-agent-mcp"})

# Create transport
logger.info("Creating SSE transport...")
sse_transport = create_sse_transport("/messages", mcp)

# Create Starlette app
app = Starlette(
    debug=True,
    routes=[
        Route("/health", health_check, methods=["GET"]),
        Route("/sse", endpoint=sse_transport.handle_sse, methods=["GET"]),
        Route("/messages", endpoint=sse_transport.handle_post_message, methods=["POST"]),
    ] + sse_transport.get_routes()
)

async def main():
    """Main entry point"""
    import os
    host = os.getenv("MEMORY_AGENT_HOST", "0.0.0.0")
    port = int(os.getenv("MEMORY_AGENT_PORT", "8094"))
    
    logger.info(f"Starting Memory Agent MCP server on {host}:{port}")
    
    config = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_level="info",
        access_log=True
    )
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(main())