"""
Memory Event Streaming Support
Real-time updates for memory operations
"""

import asyncio
from typing import Dict, Any, AsyncGenerator, Optional, Set
from datetime import datetime
import json
import logging
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class MemoryEvent:
    """Memory event structure"""
    event_type: str  # created, updated, deleted, retrieved
    user_id: str
    session_id: Optional[str]
    memory_id: Optional[str]
    memory_type: Optional[str]
    content: Optional[str]
    metadata: Dict[str, Any]
    timestamp: str
    
    def to_sse(self) -> str:
        """Convert to SSE format"""
        data = {
            "event": self.event_type,
            "data": asdict(self)
        }
        return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

class MemoryEventStream:
    """Manages memory event streaming"""
    
    def __init__(self):
        # Active subscriptions: user_id -> set of queues
        self._subscriptions: Dict[str, Set[asyncio.Queue]] = {}
        # Session subscriptions: session_id -> set of queues
        self._session_subscriptions: Dict[str, Set[asyncio.Queue]] = {}
        # Global subscriptions for all events
        self._global_subscriptions: Set[asyncio.Queue] = set()
    
    async def emit_event(self, event: MemoryEvent):
        """Emit event to all relevant subscribers"""
        # Send to user subscribers
        if event.user_id in self._subscriptions:
            for queue in self._subscriptions[event.user_id]:
                try:
                    await queue.put(event)
                except asyncio.QueueFull:
                    logger.warning(f"Queue full for user {event.user_id}")
        
        # Send to session subscribers
        if event.session_id and event.session_id in self._session_subscriptions:
            for queue in self._session_subscriptions[event.session_id]:
                try:
                    await queue.put(event)
                except asyncio.QueueFull:
                    logger.warning(f"Queue full for session {event.session_id}")
        
        # Send to global subscribers
        for queue in self._global_subscriptions:
            try:
                await queue.put(event)
            except asyncio.QueueFull:
                logger.warning("Global queue full")
    
    async def subscribe_user(
        self, 
        user_id: str, 
        queue_size: int = 100
    ) -> AsyncGenerator[MemoryEvent, None]:
        """Subscribe to events for specific user"""
        queue = asyncio.Queue(maxsize=queue_size)
        
        # Add to subscriptions
        if user_id not in self._subscriptions:
            self._subscriptions[user_id] = set()
        self._subscriptions[user_id].add(queue)
        
        try:
            while True:
                event = await queue.get()
                yield event
        finally:
            # Clean up subscription
            self._subscriptions[user_id].discard(queue)
            if not self._subscriptions[user_id]:
                del self._subscriptions[user_id]
    
    async def subscribe_session(
        self, 
        session_id: str,
        queue_size: int = 100
    ) -> AsyncGenerator[MemoryEvent, None]:
        """Subscribe to events for specific session"""
        queue = asyncio.Queue(maxsize=queue_size)
        
        # Add to subscriptions
        if session_id not in self._session_subscriptions:
            self._session_subscriptions[session_id] = set()
        self._session_subscriptions[session_id].add(queue)
        
        try:
            while True:
                event = await queue.get()
                yield event
        finally:
            # Clean up subscription
            self._session_subscriptions[session_id].discard(queue)
            if not self._session_subscriptions[session_id]:
                del self._session_subscriptions[session_id]
    
    async def subscribe_all(
        self,
        queue_size: int = 100
    ) -> AsyncGenerator[MemoryEvent, None]:
        """Subscribe to all memory events"""
        queue = asyncio.Queue(maxsize=queue_size)
        self._global_subscriptions.add(queue)
        
        try:
            while True:
                event = await queue.get()
                yield event
        finally:
            self._global_subscriptions.discard(queue)
    
    def create_event(
        self,
        event_type: str,
        user_id: str,
        session_id: Optional[str] = None,
        memory_id: Optional[str] = None,
        memory_type: Optional[str] = None,
        content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> MemoryEvent:
        """Create a new memory event"""
        return MemoryEvent(
            event_type=event_type,
            user_id=user_id,
            session_id=session_id,
            memory_id=memory_id,
            memory_type=memory_type,
            content=content,
            metadata=metadata or {},
            timestamp=datetime.utcnow().isoformat()
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get streaming statistics"""
        return {
            "user_subscriptions": len(self._subscriptions),
            "session_subscriptions": len(self._session_subscriptions),
            "global_subscriptions": len(self._global_subscriptions),
            "total_queues": sum(
                len(queues) for queues in self._subscriptions.values()
            ) + sum(
                len(queues) for queues in self._session_subscriptions.values()
            ) + len(self._global_subscriptions)
        }

# Global event stream instance
memory_event_stream = MemoryEventStream()

# Helper class for memory agent integration
class StreamingMemoryAgent:
    """Memory agent with streaming support"""
    
    def __init__(self, memory_agent, event_stream: MemoryEventStream):
        self.memory_agent = memory_agent
        self.event_stream = event_stream
    
    async def add_memory(self, *args, **kwargs) -> Dict[str, Any]:
        """Add memory with event emission"""
        result = await self.memory_agent.add_memory(*args, **kwargs)
        
        if result.get("status") == "success":
            # Emit creation event
            event = self.event_stream.create_event(
                event_type="memory_created",
                user_id=kwargs.get("user_id"),
                session_id=kwargs.get("session_id"),
                memory_id=result.get("memory_id"),
                memory_type=result.get("memory_type"),
                content=kwargs.get("content"),
                metadata={
                    "importance": result.get("importance"),
                    "timestamp": result.get("timestamp")
                }
            )
            await self.event_stream.emit_event(event)
        
        return result
    
    async def search_memories(self, *args, **kwargs) -> List[Dict[str, Any]]:
        """Search memories with event emission"""
        results = await self.memory_agent.search_memories(*args, **kwargs)
        
        # Emit retrieval event
        event = self.event_stream.create_event(
            event_type="memory_retrieved",
            user_id=kwargs.get("user_id"),
            session_id=kwargs.get("session_id"),
            metadata={
                "query": kwargs.get("query"),
                "result_count": len(results),
                "memory_types": kwargs.get("memory_types")
            }
        )
        await self.event_stream.emit_event(event)
        
        return results
    
    async def delete_memory(self, user_id: str, memory_id: str) -> bool:
        """Delete memory with event emission"""
        # Implement deletion (not in current memory agent)
        success = True  # Placeholder
        
        if success:
            event = self.event_stream.create_event(
                event_type="memory_deleted",
                user_id=user_id,
                memory_id=memory_id
            )
            await self.event_stream.emit_event(event)
        
        return success