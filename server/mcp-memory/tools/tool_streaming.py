"""
Streaming tools for Memory Agent
Real-time memory updates via SSE
"""

import asyncio
import json
from typing import AsyncGenerator, Optional
from datetime import datetime

from mcp_instance import mcp
from src.memory_event_stream import memory_event_stream, MemoryEvent

# Note: MCP doesn't have native streaming support yet, 
# so we'll implement it using long-polling or SSE wrapper

@mcp.tool(description="Subscribe to memory updates for a user")
async def subscribe_memory_updates(
    user_id: str,
    session_id: Optional[str] = None,
    duration_seconds: int = 300  # 5 minutes default
) -> str:
    """
    Subscribe to memory updates for specified duration
    Returns events that occurred during subscription period
    """
    events = []
    end_time = asyncio.get_event_loop().time() + duration_seconds
    
    # Create subscription
    if session_id:
        subscription = memory_event_stream.subscribe_session(session_id)
    else:
        subscription = memory_event_stream.subscribe_user(user_id)
    
    try:
        async for event in subscription:
            events.append(event.to_sse())
            
            # Check timeout
            if asyncio.get_event_loop().time() > end_time:
                break
                
            # Limit events to prevent overflow
            if len(events) > 100:
                break
                
    except asyncio.CancelledError:
        pass
    
    return json.dumps({
        "success": True,
        "user_id": user_id,
        "session_id": session_id,
        "event_count": len(events),
        "events": events,
        "subscription_stats": memory_event_stream.get_stats()
    })

@mcp.tool(description="Get recent memory events")
async def get_recent_events(
    user_id: str,
    event_types: Optional[list] = None,
    limit: int = 50
) -> str:
    """
    Get recent memory events (requires event history implementation)
    This is a placeholder for event history retrieval
    """
    # In a real implementation, you'd query an event store
    return json.dumps({
        "success": True,
        "user_id": user_id,
        "events": [],  # Would contain historical events
        "message": "Event history not yet implemented"
    })

# Alternative: SSE endpoint for true streaming
async def create_sse_stream(
    request,
    user_id: str,
    session_id: Optional[str] = None
) -> AsyncGenerator[str, None]:
    """
    Create SSE stream for memory updates
    This would be used in a Starlette/FastAPI endpoint
    """
    # Send initial connection event
    yield f"data: {json.dumps({'event': 'connected', 'timestamp': datetime.utcnow().isoformat()})}\n\n"
    
    # Subscribe to events
    if session_id:
        subscription = memory_event_stream.subscribe_session(session_id)
    else:
        subscription = memory_event_stream.subscribe_user(user_id)
    
    try:
        async for event in subscription:
            # Check if client is still connected
            if await request.is_disconnected():
                break
                
            # Send event as SSE
            yield event.to_sse()
            
            # Send heartbeat every 30 seconds
            if int(asyncio.get_event_loop().time()) % 30 == 0:
                yield f"data: {json.dumps({'event': 'heartbeat', 'timestamp': datetime.utcnow().isoformat()})}\n\n"
                
    except asyncio.CancelledError:
        pass
    finally:
        # Send disconnection event
        yield f"data: {json.dumps({'event': 'disconnected', 'timestamp': datetime.utcnow().isoformat()})}\n\n"

# WebSocket alternative for bidirectional streaming
class MemoryWebSocketHandler:
    """WebSocket handler for real-time memory updates"""
    
    def __init__(self):
        self.connections = {}
    
    async def connect(self, websocket, user_id: str, session_id: Optional[str] = None):
        """Handle new WebSocket connection"""
        connection_id = f"{user_id}_{session_id or 'all'}_{id(websocket)}"
        self.connections[connection_id] = {
            "websocket": websocket,
            "user_id": user_id,
            "session_id": session_id
        }
        
        # Send welcome message
        await websocket.send_json({
            "event": "connected",
            "connection_id": connection_id,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Start listening for events
        if session_id:
            subscription = memory_event_stream.subscribe_session(session_id)
        else:
            subscription = memory_event_stream.subscribe_user(user_id)
        
        try:
            async for event in subscription:
                await websocket.send_json({
                    "event": event.event_type,
                    "data": {
                        "user_id": event.user_id,
                        "session_id": event.session_id,
                        "memory_id": event.memory_id,
                        "memory_type": event.memory_type,
                        "content": event.content[:100] if event.content else None,
                        "metadata": event.metadata,
                        "timestamp": event.timestamp
                    }
                })
        except Exception as e:
            await websocket.send_json({
                "event": "error",
                "error": str(e)
            })
        finally:
            del self.connections[connection_id]
    
    async def broadcast_to_user(self, user_id: str, message: dict):
        """Broadcast message to all connections for a user"""
        for conn_id, conn in self.connections.items():
            if conn["user_id"] == user_id:
                try:
                    await conn["websocket"].send_json(message)
                except:
                    pass

# Usage example for streaming endpoint
"""
# In your server file (server_asgi_fixed.py), add:

from starlette.responses import StreamingResponse

async def memory_stream_endpoint(request):
    user_id = request.query_params.get("user_id")
    session_id = request.query_params.get("session_id")
    
    if not user_id:
        return JSONResponse({"error": "user_id required"}, status_code=400)
    
    return StreamingResponse(
        create_sse_stream(request, user_id, session_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

# Add route:
Route("/memory-stream", memory_stream_endpoint, methods=["GET"])
"""