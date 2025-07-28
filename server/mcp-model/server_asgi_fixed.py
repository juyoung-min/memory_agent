#!/usr/bin/env python3
"""Model-MCP Server with ASGI-fixed SSE support"""

import os
import sys
import argparse
import logging
import importlib
from pathlib import Path

# Add parent directory to path to import sse_asgi_fix
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

import uvicorn
from mcp_instance import mcp
from sse_asgi_fix import create_sse_asgi_app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import tools listed in tools/tool_list.txt
tool_dir = "tools"
tool_list_file = os.path.join(tool_dir, "tool_list.txt")

try:
    with open(tool_list_file, "r") as f:
        modules = [
            line.strip()
            for line in f
            if line.strip() and not line.strip().startswith("#")
        ]

    for module_name in modules:
        importlib.import_module(f"{tool_dir}.{module_name}")
        logger.info(f"Loaded tool module: {module_name}")
except Exception as e:
    logger.error(f"Error loading tools: {e}")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Model-MCP Server with ASGI Fix")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8091, help="Port to listen on")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    parser.add_argument("--log-level", default="INFO", 
                       choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                       help="Set the logging level")
    
    args = parser.parse_args()
    
    # Update logging level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    logger.info(f"Starting Model-MCP Server (ASGI Fixed) on {args.host}:{args.port}")
    logger.info(f"AI Inference Server URL: {os.getenv('AI_INFERENCE_SERVER_URL', 'Not configured')}")
    
    # Get the MCP server instance
    mcp_server = mcp._mcp_server
    
    # Create ASGI-compatible SSE app
    app = create_sse_asgi_app(mcp_server, debug=args.log_level == "DEBUG")
    
    # Run the server
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=args.log_level.lower()
    )

if __name__ == "__main__":
    main()