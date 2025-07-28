"""
SSE Transport for Memory Agent MCP
Based on the working implementation from other MCP services
"""

from mcp.server.sse import SseServerTransport
import logging

logger = logging.getLogger(__name__)

def create_sse_transport(path_prefix: str, mcp_instance):
    """Create SSE transport for MCP server"""
    
    # Create transport with the MCP instance
    transport = SseServerTransport(path_prefix)
    
    # Important: Connect the MCP instance to the transport
    # This ensures the transport can handle the registered tools
    mcp_instance._transport = transport
    
    logger.info(f"SSE transport created with path prefix: {path_prefix}")
    
    return transport