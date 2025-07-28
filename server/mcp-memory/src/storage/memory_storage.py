"""Memory Storage Backend with session_id support"""

from typing import List, Dict, Any, Optional
from ..memory_agent.memory_types import Memory, MemoryType

class MemoryStorage:
    """
    In-memory storage backend for memories
    Supports session-based organization and search
    """
    
    def __init__(self):
        self.memories: List[Memory] = []
        self._index_by_user: Dict[str, List[Memory]] = {}
        self._index_by_session: Dict[str, List[Memory]] = {}
    
    async def store_memory(self, memory: Memory) -> bool:
        """
        Store memory with proper indexing
        Returns True if successful, False otherwise
        """
        try:
            # Validate required attributes
            if not hasattr(memory, 'session_id') or memory.session_id is None:
                raise AttributeError("Memory must have session_id attribute")
            
            if not memory.user_id:
                raise ValueError("Memory must have user_id")
            
            # Store memory
            self.memories.append(memory)
            
            # Update indexes
            if memory.user_id not in self._index_by_user:
                self._index_by_user[memory.user_id] = []
            self._index_by_user[memory.user_id].append(memory)
            
            session_key = f"{memory.user_id}_{memory.session_id}"
            if session_key not in self._index_by_session:
                self._index_by_session[session_key] = []
            self._index_by_session[session_key].append(memory)
            
            return True
            
        except Exception as e:
            print(f"❌ Storage error: {e}")
            return False
    
    async def search_memories(self, user_id: str, session_id: str = None, 
                            query: str = "", memory_types: List[MemoryType] = None,
                            limit: int = 10) -> List[Memory]:
        """
        Search memories with comprehensive filtering
        """
        try:
            # Get base set of memories
            if session_id:
                session_key = f"{user_id}_{session_id}"
                candidates = self._index_by_session.get(session_key, [])
            else:
                candidates = self._index_by_user.get(user_id, [])
            
            results = []
            
            for memory in candidates:
                # Filter by memory types if specified
                if memory_types and memory.type not in memory_types:
                    continue
                
                # Filter by text query if specified
                if query and query.lower() not in memory.content.lower():
                    continue
                
                results.append(memory)
            
            # Sort by importance and timestamp (most important and recent first)
            results.sort(key=lambda m: (m.importance, m.timestamp), reverse=True)
            
            return results[:limit]
            
        except Exception as e:
            print(f"❌ Search error: {e}")
            return []
    
    async def get_user_memories(self, user_id: str, session_id: str = None, 
                               limit: int = 100) -> List[Memory]:
        """Get all memories for a user, optionally filtered by session"""
        return await self.search_memories(user_id, session_id, limit=limit)
    
    async def get_memory_stats(self, user_id: str, session_id: str = None) -> Dict[str, Any]:
        """Get comprehensive memory statistics"""
        try:
            memories = await self.get_user_memories(user_id, session_id)
            
            # Type distribution
            type_distribution = {}
            importance_scores = []
            session_distribution = {}
            
            for memory in memories:
                # Type stats
                type_str = memory.type.value
                type_distribution[type_str] = type_distribution.get(type_str, 0) + 1
                
                # Importance stats
                importance_scores.append(memory.importance)
                
                # Session stats
                sess = memory.session_id
                session_distribution[sess] = session_distribution.get(sess, 0) + 1
            
            avg_importance = sum(importance_scores) / len(importance_scores) if importance_scores else 0.0
            
            return {
                "total_memories": len(memories),
                "type_distribution": type_distribution,
                "session_distribution": session_distribution,
                "average_importance": round(avg_importance, 2),
                "importance_range": {
                    "min": min(importance_scores) if importance_scores else 0,
                    "max": max(importance_scores) if importance_scores else 0
                },
                "user_id": user_id,
                "session_id": session_id
            }
            
        except Exception as e:
            print(f"❌ Stats error: {e}")
            return {"error": str(e)}
    
    async def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory by ID"""
        try:
            # Find and remove memory
            memory_to_remove = None
            for memory in self.memories:
                if memory.id == memory_id:
                    memory_to_remove = memory
                    break
            
            if memory_to_remove:
                self.memories.remove(memory_to_remove)
                
                # Update indexes
                user_memories = self._index_by_user.get(memory_to_remove.user_id, [])
                if memory_to_remove in user_memories:
                    user_memories.remove(memory_to_remove)
                
                session_key = f"{memory_to_remove.user_id}_{memory_to_remove.session_id}"
                session_memories = self._index_by_session.get(session_key, [])
                if memory_to_remove in session_memories:
                    session_memories.remove(memory_to_remove)
                
                return True
            
            return False
            
        except Exception as e:
            print(f"❌ Delete error: {e}")
            return False
    
    async def update_memory(self, memory_id: str, updates: Dict[str, Any]) -> bool:
        """Update a memory with new values"""
        try:
            for memory in self.memories:
                if memory.id == memory_id:
                    for key, value in updates.items():
                        if hasattr(memory, key):
                            setattr(memory, key, value)
                    return True
            return False
            
        except Exception as e:
            print(f"❌ Update error: {e}")
            return False
    
    def get_storage_info(self) -> Dict[str, Any]:
        """Get information about the storage backend"""
        return {
            "backend_type": "MemoryStorage",
            "total_memories": len(self.memories),
            "indexed_users": len(self._index_by_user),
            "indexed_sessions": len(self._index_by_session),
            "supports_session_id": True,
            "supports_search": True,
            "supports_filtering": True
        }