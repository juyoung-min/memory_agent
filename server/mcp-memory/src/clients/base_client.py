# base_client.py
import logging
from typing import Dict, Any, Optional
from mcp import ClientSession
from mcp.client.sse import sse_client
import json

logger = logging.getLogger(__name__)

class InternalMCPClient:
    """Internal client for server-to-server MCP communication via SSE - minimal version"""
    
    def __init__(self, server_url: str, timeout: int = 30):
        self.server_url = server_url
        self.timeout = timeout
        
    async def call_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Call an MCP tool on a remote server"""
        
        try:
            logger.info(f"Calling tool {tool_name} on {self.server_url}")
            
            # Create fresh connection for each call
            async with sse_client(url=self.server_url) as streams:
                async with ClientSession(*streams) as session:
                    await session.initialize()
                    
                    # Call the tool
                    result = await session.call_tool(tool_name, params)
                    
                    if not result.content:
                        logger.error(f"No content in response from {tool_name}")
                        return {
                            "success": False,
                            "error": "No content in tool response",
                            "error_type": "EmptyResponse"
                        }
                    
                    # Parse the tool response
                    response_text = result.content[0].text
                    
                    try:
                        # Try to parse as JSON
                        parsed = json.loads(response_text)
                        return parsed
                    except json.JSONDecodeError:
                        # Return as text if not JSON
                        return {
                            "success": True,
                            "result": response_text
                        }
                        
        except Exception as e:
            logger.error(f"Error calling tool {tool_name}: {e}")
            return {
                "success": False,
                "error": f"Tool call failed: {str(e)}",
                "error_type": type(e).__name__
            }
            
    async def close(self):
        """No-op for compatibility"""
        pass