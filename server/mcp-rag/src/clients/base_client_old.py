import logging
from typing import Dict, Any, Optional
from mcp import ClientSession
from mcp.client.sse import sse_client
import json
import asyncio

logger = logging.getLogger(__name__)

class InternalMCPClient:
    """Internal client for server-to-server MCP communication via SSE with auto-reconnect"""
    
    def __init__(self, server_url: str, timeout: int = 30):
        self.server_url = server_url
        self.timeout = timeout
        self.session: Optional[ClientSession] = None
        self._streams_context = None
        self._session_context = None
        self._connected = False
        self._connection_lock = asyncio.Lock()
        
    async def _disconnect(self):
        """Disconnect the current SSE connection"""
        if self._connected:
            try:
                if self._session_context:
                    await self._session_context.__aexit__(None, None, None)
                if self._streams_context:
                    await self._streams_context.__aexit__(None, None, None)
            except Exception as e:
                logger.warning(f"Error during disconnect: {e}")
            finally:
                self._connected = False
                self.session = None
                self._session_context = None
                self._streams_context = None
                
    async def _ensure_connected(self):
        """Ensure SSE connection is established with reconnection"""
        async with self._connection_lock:
            # Test if current connection is healthy
            if self._connected and self.session:
                try:
                    # Quick health check - list tools
                    await asyncio.wait_for(
                        self.session.list_tools(), 
                        timeout=5.0
                    )
                    return  # Connection is healthy
                except Exception as e:
                    logger.warning(f"Connection health check failed: {e}")
                    await self._disconnect()
                    
            # Establish new connection
            try:
                logger.info(f"Establishing SSE connection to {self.server_url}")
                self._streams_context = sse_client(url=self.server_url)
                streams = await self._streams_context.__aenter__()
                self._session_context = ClientSession(*streams)
                self.session = await self._session_context.__aenter__()
                await self.session.initialize()
                self._connected = True
                logger.info(f"SSE connection established to {self.server_url}")
            except Exception as e:
                logger.error(f"Failed to establish SSE connection: {e}")
                self._connected = False
                raise
                
    async def call_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Call an MCP tool on a remote server with retry"""
        max_retries = 3
        last_error = None
        
        for attempt in range(max_retries):
            try:
                # Ensure connection is established
                await self._ensure_connected()
                
                # Call the tool through MCP session
                result = await asyncio.wait_for(
                    self.session.call_tool(tool_name, params),
                    timeout=self.timeout
                )
                
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
                    
            except asyncio.TimeoutError:
                last_error = f"Timeout calling {tool_name}"
                logger.warning(f"Attempt {attempt + 1}/{max_retries}: {last_error}")
                await self._disconnect()
                if attempt < max_retries - 1:
                    await asyncio.sleep(1 * (attempt + 1))  # Exponential backoff
                    
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Attempt {attempt + 1}/{max_retries}: Error calling tool {tool_name}: {e}")
                await self._disconnect()
                if attempt < max_retries - 1:
                    await asyncio.sleep(1 * (attempt + 1))  # Exponential backoff
                    
        # All retries failed
        logger.error(f"All retries failed for {tool_name}: {last_error}")
        return {
            "success": False,
            "error": f"Tool call failed after {max_retries} attempts: {last_error}",
            "error_type": "MaxRetriesExceeded"
        }
            
    async def close(self):
        """Close the SSE connection"""
        if self._connected:
            try:
                # Simple cleanup without complex context management
                self._connected = False
                self.session = None
                logger.info("SSE connection marked for cleanup")
            except Exception as e:
                logger.warning(f"Error during close: {e}")