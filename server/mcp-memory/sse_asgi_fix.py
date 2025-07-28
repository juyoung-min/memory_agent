#!/usr/bin/env python3
"""
SSE ASGI Compatibility Fix

This module provides a wrapper to make MCP's SseServerTransport compatible with ASGI frameworks like Starlette.
"""

import logging
from typing import Callable
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Route
from mcp.server import Server
from mcp.server.sse import SseServerTransport

logger = logging.getLogger(__name__)

def create_sse_asgi_app(mcp_server: Server, *, debug: bool = False) -> Starlette:
    """
    Create a Starlette application with proper SSE ASGI handling.
    
    This fixes the TypeError: 'SseServerTransport' object is not callable
    by properly wrapping the SSE transport in ASGI-compatible handlers.
    """
    
    # Create SSE transport
    sse_transport = SseServerTransport("/messages/")
    
    async def handle_sse(request: Request):
        """Handle SSE GET connection for streaming"""
        logger.info(f"SSE connection established from {request.client}")
        try:
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
            # Return empty response to satisfy ASGI
            return Response("", status_code=200)
        except Exception as e:
            logger.error(f"Error in SSE connection: {e}", exc_info=True)
            return Response(f"SSE Error: {str(e)}", status_code=500)
    
    async def handle_messages(request: Request):
        """Handle POST to /messages/ endpoint with ASGI compatibility"""
        logger.info(f"Message POST received: {request.url}")
        logger.debug(f"Request headers: {dict(request.headers)}")
        logger.debug(f"Request method: {request.method}")
        
        # Check for session_id
        session_id = request.query_params.get("session_id")
        if not session_id:
            logger.error("Missing session_id in request")
            return Response("Missing session_id", status_code=400)
        
        logger.debug(f"Session ID: {session_id}")
        
        try:
            # Create a wrapper to make handle_post_message ASGI-compatible
            class ASGIWrapper:
                def __init__(self, transport):
                    self.transport = transport
                    self.response_data = []
                    self.status_code = 200
                    self.headers = []
                
                async def __call__(self, scope, receive, send):
                    # Intercept the send to capture response
                    async def wrapped_send(message):
                        logger.debug(f"Intercepted message type: {message.get('type')}")
                        logger.debug(f"Message content: {message}")
                        
                        if message["type"] == "http.response.start":
                            self.status_code = message.get("status", 200)
                            self.headers = message.get("headers", [])
                            logger.debug(f"Response started with status: {self.status_code}")
                        elif message["type"] == "http.response.body":
                            body = message.get("body", b"")
                            if body:
                                self.response_data.append(body)
                                logger.debug(f"Body chunk received: {len(body)} bytes")
                    
                    # Call the transport's handler
                    logger.debug("Calling SSE transport handle_post_message")
                    result = await self.transport.handle_post_message(scope, receive, wrapped_send)
                    logger.debug(f"handle_post_message returned: {result}")
            
            # Create wrapper instance
            wrapper = ASGIWrapper(sse_transport)
            
            # Execute the wrapped handler
            logger.debug("Executing wrapper")
            await wrapper(request.scope, request.receive, request._send)
            
            logger.debug(f"Wrapper execution complete. Response data: {len(wrapper.response_data)} chunks")
            logger.debug(f"Status code: {wrapper.status_code}, Headers: {wrapper.headers}")
            
            # Return the captured response
            if wrapper.response_data:
                response_body = b"".join(wrapper.response_data)
                logger.debug(f"Total response body size: {len(response_body)} bytes")
                
                # Convert ASGI headers (list of tuples of bytes) to dict of strings
                header_dict = {}
                for key_bytes, value_bytes in wrapper.headers:
                    key_str = key_bytes.decode('latin-1')
                    value_str = value_bytes.decode('latin-1')
                    header_dict[key_str] = value_str
                
                logger.debug(f"Returning Response with status {wrapper.status_code}")
                return Response(
                    content=response_body,
                    status_code=wrapper.status_code,
                    headers=header_dict
                )
            else:
                # If no response was captured, return a success response
                logger.debug("No response data captured, returning 204")
                return Response("", status_code=204)
                
        except Exception as e:
            logger.error(f"Error handling message: {e}", exc_info=True)
            return Response(f"Internal Server Error: {str(e)}", status_code=500)
    
    async def handle_catchall(request: Request):
        """Catch all unhandled routes for debugging"""
        logger.warning(f"Unhandled route accessed: {request.method} {request.url.path}")
        logger.warning(f"Full URL: {request.url}")
        logger.warning(f"Headers: {dict(request.headers)}")
        return Response(f"Not Found: {request.url.path}", status_code=404)
    
    # Create Starlette app with fixed routes
    app = Starlette(
        routes=[
            Route("/sse", endpoint=handle_sse, methods=["GET"]),
            Route("/messages/", endpoint=handle_messages, methods=["POST"]),
            Route("/{path:path}", endpoint=handle_catchall),  # Catch all other routes
        ],
        debug=debug
    )
    
    logger.info("SSE ASGI app created successfully")
    return app