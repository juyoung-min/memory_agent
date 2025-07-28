"""
MCP Instance for Memory Agent
"""

from mcp.server.fastmcp import FastMCP

# Create MCP instance
mcp = FastMCP("Memory-Agent-MCP")

# Log initialization
import logging
logger = logging.getLogger(__name__)
logger.info("Memory Agent MCP instance created")