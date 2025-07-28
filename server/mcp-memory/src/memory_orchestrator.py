"""
Memory Orchestrator with Single Responsibility
Each method has one clear purpose
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import logging
import json

from .memory_agent import MemoryAgent
from .memory_agent.memory_types import MemoryType
from .clients import InternalMCPClient

logger = logging.getLogger(__name__)

class MemoryOrchestrator:
    """Orchestrates memory operations with clear separation of concerns"""
    
    def __init__(
        self,
        memory_agent: MemoryAgent,
        rag_client: InternalMCPClient,
        db_client: InternalMCPClient,
        model_client: InternalMCPClient
    ):
        self.memory_agent = memory_agent
        self.rag_client = rag_client
        self.db_client = db_client
        self.model_client = model_client
    
    async def store_memory(
        self,
        user_id: str,
        content: str,
        session_id: str,
        memory_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Single responsibility: Store a memory"""
        
        # Analyze and classify if type not provided
        if not memory_type:
            memory_type = await self.analyze_memory_type(content)
        
        # Calculate importance
        importance = await self.calculate_importance(content, memory_type)
        
        # Store the memory
        result = await self.memory_agent.add_memory(
            user_id=user_id,
            session_id=session_id,
            content=content,
            memory_type=memory_type,
            importance=importance,
            metadata=metadata
        )
        
        # Store in RAG if needed (conversation/experience types)
        if memory_type in ["conversation", "experience"]:
            await self._store_in_rag(user_id, content, memory_type, result.get("memory_id"))
        
        return result
    
    async def retrieve_memories(
        self,
        user_id: str,
        query: str,
        memory_types: Optional[List[str]] = None,
        session_id: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Single responsibility: Retrieve memories"""
        
        # Get embedding for query
        embedding = await self._get_embedding(query)
        
        # Search in appropriate storage
        if memory_types and "conversation" in memory_types:
            # Use RAG for conversations
            return await self._search_rag(user_id, query, session_id, limit)
        else:
            # Use direct DB search
            return await self._search_db(user_id, embedding, memory_types, session_id, limit)
    
    async def get_context(
        self,
        user_id: str,
        current_message: str,
        session_id: Optional[str] = None,
        context_size: int = 5
    ) -> Dict[str, Any]:
        """Single responsibility: Build context for current message"""
        
        # Search relevant conversations
        conversations = await self.retrieve_memories(
            user_id, current_message, ["conversation"], session_id, context_size
        )
        
        # Search relevant facts/preferences
        user_info = await self.retrieve_memories(
            user_id, current_message, ["fact", "preference", "identity"], None, 3
        )
        
        return {
            "conversations": conversations,
            "user_info": user_info,
            "total_context": len(conversations) + len(user_info)
        }
    
    async def analyze_memory_type(self, content: str) -> str:
        """Single responsibility: Analyze and classify memory type"""
        return self.memory_agent.intelligence.extract_memory_type(content, {})
    
    async def calculate_importance(self, content: str, memory_type: str) -> float:
        """Single responsibility: Calculate memory importance"""
        return self.memory_agent.intelligence.calculate_importance(
            content, MemoryType(memory_type), {}
        )
    
    async def generate_response(
        self,
        prompt: str,
        context: Dict[str, Any],
        model: str = "EXAONE-3.5-2.4B-Instruct"
    ) -> str:
        """Single responsibility: Generate LLM response"""
        
        # Build prompt with context
        context_prompt = self._build_context_prompt(prompt, context)
        
        # Call LLM
        response = await self.model_client.call_tool(
            "generate_completion",
            {
                "prompt": context_prompt,
                "model": model,
                "temperature": 0.7,
                "max_tokens": 500
            }
        )
        
        return response.get("text", "")
    
    async def _get_embedding(self, text: str) -> List[float]:
        """Get embedding through RAG-MCP"""
        response = await self.rag_client.call_tool(
            "rag_generate_embedding",
            {"text": text, "model": "bge-m3"}
        )
        return response.get("embedding", [])
    
    async def _store_in_rag(
        self, 
        user_id: str, 
        content: str, 
        memory_type: str,
        memory_id: str
    ) -> bool:
        """Store in RAG for better retrieval"""
        result = await self.rag_client.call_tool(
            "rag_save_document",
            {
                "content": content,
                "namespace": f"{user_id}_{memory_type}s",
                "document_id": memory_id,
                "metadata": {
                    "user_id": user_id,
                    "memory_type": memory_type,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        )
        return result.get("success", False)
    
    async def _search_rag(
        self,
        user_id: str,
        query: str,
        session_id: Optional[str],
        limit: int
    ) -> List[Dict[str, Any]]:
        """Search in RAG storage"""
        result = await self.rag_client.call_tool(
            "rag_search",
            {
                "query": query,
                "namespace": f"{user_id}_conversations",
                "limit": limit,
                "include_content": True
            }
        )
        return result.get("results", [])
    
    async def _search_db(
        self,
        user_id: str,
        embedding: List[float],
        memory_types: Optional[List[str]],
        session_id: Optional[str],
        limit: int
    ) -> List[Dict[str, Any]]:
        """Search in database"""
        filters = {"user_id": user_id}
        if session_id:
            filters["session_id"] = session_id
        if memory_types:
            filters["memory_type"] = {"$in": memory_types}
        
        result = await self.db_client.call_tool(
            "db_search_vectors",
            {
                "table": "user_memories",
                "query_vector": embedding,
                "filters": filters,
                "limit": limit
            }
        )
        return result.get("results", [])
    
    def _build_context_prompt(self, prompt: str, context: Dict[str, Any]) -> str:
        """Build prompt with context"""
        parts = []
        
        # Add conversation context
        if context.get("conversations"):
            parts.append("=== Recent Conversations ===")
            for conv in context["conversations"]:
                parts.append(conv.get("content", ""))
            parts.append("")
        
        # Add user info
        if context.get("user_info"):
            parts.append("=== User Information ===")
            for info in context["user_info"]:
                parts.append(f"[{info.get('type')}] {info.get('content')}")
            parts.append("")
        
        parts.append(f"Current Message: {prompt}")
        parts.append("\nResponse:")
        
        return "\n".join(parts)