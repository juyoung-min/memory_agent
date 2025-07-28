"""
Memory Agent Orchestrator Tool
Integrates memory management with RAG-MCP
"""

import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid

from mcp_instance import mcp
from src.clients import InternalMCPClient
from src.memory_agent import MemoryAgent
from src.memory_agent.memory_types import MemoryType
from src.config import get_config
from src.embedding_utils import get_embedding_dimension, ensure_table_with_dimension, get_embedding_from_rag

# Initialize configuration
config = get_config()
logger = logging.getLogger(__name__)

# Initialize clients
rag_client = InternalMCPClient("http://mcp-rag:8093/sse", timeout=30)
db_client = InternalMCPClient("http://mcp-db:8092/sse", timeout=30)
model_client = InternalMCPClient("http://model-mcp:8091/sse", timeout=30)

# Initialize Memory Agent
memory_agent = MemoryAgent(
    storage=None,  # Will use DB-MCP for storage
    enable_intelligence=True
)

@mcp.tool(description="Process and store user message with appropriate memory type")
async def process_message(
    user_id: str,
    message: str,
    session_id: str,
    memory_type: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> str:
    """
    Process and store user message with intelligent memory management
    
    Args:
        user_id: User identifier
        message: User's message
        session_id: Session identifier
        memory_type: Memory type (auto-classify if not provided)
        metadata: Additional metadata
    """
    
    if not message or not user_id:
        return json.dumps({
            "success": False,
            "error": "Message and user_id are required",
            "error_type": "ValidationError"
        })
    
    try:
        logger.info(f"Processing message for user {user_id}: {message[:50]}...")
        
        # Step 1: Analyze and store message
        memory_result = await memory_agent.add_memory(
            user_id=user_id,
            session_id=session_id,
            content=message,
            memory_type=memory_type,  # Will auto-classify if None
            importance=None,   # Auto-calculate
            metadata={
                "source": "user_message",
                "timestamp": datetime.utcnow().isoformat(),
                **(metadata or {})
            }
        )
        
        # Step 2: Based on memory type, decide storage strategy
        stored_type = memory_result.get("memory_type", "unknown")
        
        # All memories are now stored in DB only, not RAG
        logger.info(f"Stored {stored_type} memory in database")
        
        return json.dumps({
            "success": memory_result["status"] == "success",
            "memory_id": memory_result.get("memory_id"),
            "memory_type": stored_type,
            "importance": memory_result.get("importance"),
            "rag_stored": False,  # All memories stored in DB only
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error in process_message: {e}", exc_info=True)
        return json.dumps({
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        })

@mcp.tool(description="Retrieve conversation history from database")
async def get_conversation_history(
    user_id: str,
    query: str,
    session_id: Optional[str] = None,
    limit: int = 10,
    time_range: Optional[Dict[str, str]] = None
) -> str:
    """
    Retrieve conversation history from database using semantic search
    
    Args:
        user_id: User identifier
        query: Search query for conversations
        session_id: Optional session filter
        limit: Number of results
        time_range: Optional time range filter
    """
    try:
        # Use search_user_memories with conversation filter
        logger.info(f"Retrieving conversation history for user {user_id} from database")
        
        # Search for conversation memories
        search_result = await search_user_memories(
            user_id=user_id,
            query=query,
            session_id=session_id,
            limit=limit,
            memory_types=["conversation"]
        )
        
        search_data = json.loads(search_result)
        
        if not search_data.get("success"):
            return json.dumps({
                "success": False,
                "error": "Failed to search conversation history",
                "conversations": []
            })
        
        # Format results with conversation context
        conversations = []
        for mem in search_data.get("memories", []):
            conversations.append({
                "content": mem.get("content"),
                "similarity": mem.get("similarity"),
                "session_id": mem.get("session_id"),
                "timestamp": mem.get("timestamp"),
                "memory_id": mem.get("id"),
                "importance": mem.get("importance", 5.0)
            })
        
        return json.dumps({
            "success": True,
            "conversations": conversations,
            "count": len(conversations),
            "query": query,
            "user_id": user_id,
            "source": "database"
        })
        
    except Exception as e:
        logger.error(f"Error retrieving conversation history: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "conversations": []
        })

@mcp.tool(description="Search user memories of specific types")
async def search_user_memories(
    user_id: str,
    query: str,
    session_id: Optional[str] = None,
    limit: int = 10,
    memory_types: Optional[List[str]] = None
) -> str:
    """
    Search user's memories using semantic similarity
    """
    try:
        # Get embedding model from config
        embedding_model = config.intelligence.language_models.get("embedding", "bge-m3")
        
        # First ensure the user_memories table exists with correct dimension
        dimension = await get_embedding_dimension(embedding_model, rag_client)
        table_created = await ensure_table_with_dimension(
            db_client,
            "user_memories",
            dimension,
            additional_columns={
                "user_id": "TEXT NOT NULL",
                "session_id": "TEXT",
                "memory_type": "TEXT"
            }
        )
        
        if not table_created:
            logger.warning("Could not ensure user_memories table exists")
        
        # Generate embedding through RAG-MCP (which uses model-mcp internally)
        query_vector, actual_dimension = await get_embedding_from_rag(
            rag_client,
            query,
            embedding_model
        )
        
        if not query_vector:
            return json.dumps({
                "success": False,
                "error": "Failed to generate embedding",
                "memories": []
            })
        
        # Build filters
        filters = {"user_id": user_id}
        if session_id:
            filters["session_id"] = session_id
        if memory_types:
            filters["memory_type"] = {"$in": memory_types}
        
        # Search in DB
        search_response = await db_client.call_tool(
            "db_search_vectors",
            {
                "table": "user_memories",
                "query_vector": query_vector,
                "filters": filters,
                "limit": limit,
                "similarity_threshold": 0.5
            }
        )
        
        memories = search_response.get("results", [])
        
        return json.dumps({
            "success": True,
            "memories": memories,
            "count": len(memories),
            "embedding_dimension": actual_dimension
        })
        
    except Exception as e:
        logger.error(f"Error searching memories: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "memories": []
        })

@mcp.tool(description="Get user memory statistics and patterns")
async def get_user_memory_stats(user_id: str, session_id: Optional[str] = None) -> str:
    """
    Get statistics about user's stored memories
    """
    try:
        # Get stats from storage
        stats = await memory_agent.storage.get_memory_stats(user_id, session_id)
        
        return json.dumps({
            "success": True,
            "stats": stats,
            "user_id": user_id,
            "session_id": session_id
        })
        
    except Exception as e:
        logger.error(f"Error getting memory stats: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "stats": {}
        })

@mcp.tool(description="Store memory with type-specific handling")
async def store_memory_by_type(
    user_id: str,
    content: str,
    memory_type: str,
    session_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> str:
    """
    Store memory with specific handling based on type
    
    Memory types and their storage strategies:
    - conversation: Store in RAG-MCP for retrieval
    - fact: Store locally with high importance
    - preference: Store locally for personalization
    - experience: Store in RAG-MCP if significant
    - context: Store locally for session continuity
    """
    try:
        # Validate memory type
        valid_types = ["fact", "preference", "identity", "profession", "skill", 
                      "goal", "hobby", "experience", "context", "conversation"]
        
        if memory_type not in valid_types:
            return json.dumps({
                "success": False,
                "error": f"Invalid memory type. Must be one of: {valid_types}"
            })
        
        logger.info(f"Storing {memory_type} memory for user {user_id}")
        
        # Store in memory agent first
        memory_result = await memory_agent.add_memory(
            user_id=user_id,
            session_id=session_id or f"session_{datetime.now().strftime('%Y%m%d')}",
            content=content,
            memory_type=memory_type,
            importance=None,  # Auto-calculate based on type
            metadata={
                "source": "explicit_storage",
                "timestamp": datetime.utcnow().isoformat(),
                **(metadata or {})
            }
        )
        
        # All memories are now stored in DB only, not RAG
        rag_stored = False
        rag_namespace = None
        
        logger.info(f"Stored {memory_type} memory in database with importance {memory_result.get('importance', 5.0)}")
        
        return json.dumps({
            "success": memory_result["status"] == "success",
            "memory_id": memory_result.get("memory_id"),
            "memory_type": memory_type,
            "importance": memory_result.get("importance"),
            "rag_stored": rag_stored,
            "rag_namespace": rag_namespace,
            "storage_strategy": get_storage_strategy(memory_type),
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error storing memory by type: {e}")
        return json.dumps({
            "success": False,
            "error": str(e)
        })

@mcp.tool(description="Process user prompt with automatic memory management")
async def process_user_prompt(
    user_id: str,
    prompt: str,
    session_id: str,
    auto_store: bool = True,
    generate_response: bool = True
) -> str:
    """
    Automatically handle user prompt with intelligent memory operations
    
    This tool:
    1. Searches relevant memories for context
    2. Stores the prompt as appropriate memory type
    3. Generates a response using context
    4. Stores the response as conversation memory
    
    Args:
        user_id: User identifier
        prompt: User's prompt/message
        session_id: Session identifier
        auto_store: Whether to automatically store memories
        generate_response: Whether to generate a response
    """
    try:
        logger.info(f"Processing prompt for user {user_id}: {prompt[:50]}...")
        
        # Step 1: Search for relevant context from past memories
        # Search conversations first (using RAG)
        conversation_context = await get_conversation_history(
            user_id=user_id,
            query=prompt,
            session_id=None,  # Search across all sessions
            limit=5
        )
        conv_results = json.loads(conversation_context).get("conversations", [])
        
        # Search other memory types
        memory_context = await search_user_memories(
            user_id=user_id,
            query=prompt,
            limit=5
        )
        mem_results = json.loads(memory_context).get("memories", [])
        
        # Step 2: Analyze the prompt to determine memory type
        memory_analysis = memory_agent.intelligence.extract_memory_type(prompt, {})
        importance = memory_agent.intelligence.calculate_importance(
            prompt, 
            memory_analysis, 
            {"user_memory_count": len(conv_results) + len(mem_results)}
        )
        
        # Step 3: Store the prompt if important enough
        stored_memory = None
        if auto_store and importance >= 4.0:  # Lower threshold for conversations
            # Determine if this is a conversation or specific memory type
            if memory_analysis == MemoryType.CONVERSATION or "?" in prompt:
                # Store as conversation for RAG retrieval
                store_result = await store_memory_by_type(
                    user_id=user_id,
                    content=f"User: {prompt}",
                    memory_type="conversation",
                    session_id=session_id,
                    metadata={"role": "user", "timestamp": datetime.utcnow().isoformat()}
                )
            else:
                # Store as specific type
                store_result = await store_memory_by_type(
                    user_id=user_id,
                    content=prompt,
                    memory_type=memory_analysis.value,
                    session_id=session_id
                )
            
            stored_memory = json.loads(store_result)
        
        # Step 4: Generate response if requested
        response_content = ""
        if generate_response:
            # Build context from memories
            context_parts = []
            
            # Add conversation context - show full content for recent messages
            if conv_results:
                context_parts.append("=== Recent Conversation History ===")
                for i, conv in enumerate(conv_results[:5]):  # Show more conversations
                    # Don't truncate conversation content
                    context_parts.append(f"{i+1}. {conv['content']}")
                context_parts.append("")  # Empty line
            
            # Add other memory context
            if mem_results:
                context_parts.append("=== User Information ===")
                for mem in mem_results[:3]:
                    context_parts.append(f"- [{mem.get('type', 'info')}] {mem['content']}")
                context_parts.append("")  # Empty line
            
            full_context = "\n".join(context_parts) if context_parts else ""
            
            # Generate response using Model-MCP with better prompt
            generation_prompt = f"""You are a helpful assistant with access to the user's conversation history.

{full_context}
Current User Message: {prompt}

Instructions:
1. If the user asks about previous messages or questions, refer to the Recent Conversation History above
2. Answer in the same language as the user (Korean if they use Korean)
3. Be specific and accurate when recalling previous conversations
4. For questions like "what did I just ask?", look at the most recent message in the conversation history

Response:"""

            model_response = await model_client.call_tool(
                "generate_completion",
                {
                    "prompt": generation_prompt,
                    "model": "EXAONE-3.5-2.4B-Instruct",
                    "temperature": 0.7,
                    "max_tokens": 500
                }
            )
            
            response_content = model_response.get("text", "I understand. Let me help you with that.")
            
            # Store the response as conversation memory
            if auto_store:
                await store_memory_by_type(
                    user_id=user_id,
                    content=f"Assistant: {response_content[:500]}",
                    memory_type="conversation",
                    session_id=session_id,
                    metadata={"role": "assistant", "timestamp": datetime.utcnow().isoformat()}
                )
        
        # Step 5: Return comprehensive result
        return json.dumps({
            "success": True,
            "response": response_content,
            "memory_operations": {
                "context_found": {
                    "conversations": len(conv_results),
                    "memories": len(mem_results)
                },
                "prompt_analysis": {
                    "detected_type": memory_analysis.value if isinstance(memory_analysis, MemoryType) else str(memory_analysis),
                    "importance": importance,
                    "stored": stored_memory is not None
                },
                "storage_details": stored_memory if stored_memory else None
            },
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error processing user prompt: {e}", exc_info=True)
        return json.dumps({
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        })

@mcp.tool(description="Delete user memory by ID")
async def delete_user_memory(user_id: str, memory_id: str) -> str:
    """
    Delete a specific memory
    """
    try:
        # Delete from vector database
        delete_response = await db_client.call_tool(
            "db_delete_vector",
            {
                "table": "user_memories",
                "id": memory_id,
                "filters": {"user_id": user_id}  # Security check
            }
        )
        
        return json.dumps({
            "success": delete_response.get("success", False),
            "memory_id": memory_id,
            "message": "Memory deleted successfully" if delete_response.get("success") else "Failed to delete memory"
        })
        
    except Exception as e:
        logger.error(f"Error deleting memory: {e}")
        return json.dumps({
            "success": False,
            "error": str(e)
        })

# Helper functions

def get_storage_strategy(memory_type: str) -> str:
    """Get storage strategy description for memory type"""
    strategies = {
        "conversation": "RAG-indexed for conversation retrieval",
        "experience": "RAG-indexed for experience search",
        "fact": "Local storage with importance weighting",
        "preference": "Local storage for personalization",
        "identity": "High-importance local storage",
        "profession": "High-importance local storage",
        "skill": "Local storage with categorization",
        "goal": "Local storage with timeline tracking",
        "hobby": "Local storage for interest matching",
        "context": "Session-scoped local storage"
    }
    return strategies.get(memory_type, "Standard local storage")

def should_use_rag_for_type(memory_type: str, importance: float = 5.0) -> bool:
    """Determine if memory type should be stored in RAG"""
    # Always use RAG for these types
    if memory_type in ["conversation", "experience"]:
        return True
    
    # Use RAG for high-importance memories of certain types
    if memory_type in ["fact", "identity", "profession"] and importance >= 8:
        return True
    
    return False

# Initialize on module load
logger.info("Memory Agent Orchestrator tools loaded successfully")