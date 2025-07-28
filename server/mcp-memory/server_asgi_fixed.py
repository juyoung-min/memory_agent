"""
Memory Agent MCP Server with ASGI fix for SSE
"""

import asyncio
import logging
import sys
import os

# Add parent directory to path for sse_asgi_fix
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, '/app')  # For Docker

from starlette.applications import Starlette
from starlette.routing import Route
from starlette.responses import JSONResponse
import uvicorn

# Import ASGI fix
try:
    from sse_asgi_fix import create_sse_asgi_app
except ImportError:
    print("Warning: sse_asgi_fix not found, server may have issues with SSE")
    create_sse_asgi_app = None

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import after logging is configured
from mcp_instance import mcp

# Import tools
from tools import tool_memory_orchestrator_sse

# Get the MCP server instance
mcp_server = mcp._mcp_server

# Create ASGI-compatible SSE app
if create_sse_asgi_app:
    logger.info("Creating ASGI-compatible SSE app")
    app = create_sse_asgi_app(mcp_server)
else:
    # Fallback if sse_asgi_fix is not available
    logger.warning("Using fallback app creation")
    from starlette.applications import Starlette
    from starlette.routing import Route
    from starlette.responses import JSONResponse
    
    async def health_check(request):
        """Health check endpoint"""
        return JSONResponse({"status": "healthy", "service": "memory-agent-mcp"})
    
    app = Starlette(
        debug=True,
        routes=[
            Route("/health", health_check, methods=["GET"]),
        ]
    )

async def main():
    """Main entry point"""
    host = os.getenv("SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("SERVER_PORT", "8094"))
    
    logger.info(f"Starting Memory Agent MCP server on {host}:{port}")
    logger.info("Available tools:")
    try:
        response = await mcp.list_tools()
        if hasattr(response, 'tools'):
            for tool in response.tools:
                logger.info(f"  - {tool.name}: {tool.description}")
        else:
            # response is a list
            for tool in response:
                logger.info(f"  - {tool.name}: {tool.description}")
    except Exception as e:
        logger.warning(f"Could not list tools: {e}")
    
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
    # Command line argument support
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8094)
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()
    
    os.environ["SERVER_HOST"] = args.host
    os.environ["SERVER_PORT"] = str(args.port)
    
    asyncio.run(main())