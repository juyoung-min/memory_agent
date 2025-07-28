"""
Refactored Memory Orchestrator Tools
Using Single Responsibility Principle and new features
"""

import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from mcp_instance import mcp
from src.memory_orchestrator import MemoryOrchestrator
from src.memory_agent import MemoryAgent
from src.memory_agent.hierarchical_memory_types import HierarchicalMemoryType, MemoryClassification
from src.memory_event_stream import memory_event_stream, StreamingMemoryAgent
from src.clients import InternalMCPClient
from src.config import get_config

# Initialize
config = get_config()
logger = logging.getLogger(__name__)

# Initialize clients
rag_client = InternalMCPClient("http://mcp-rag:8093/sse", timeout=30)
db_client = InternalMCPClient("http://mcp-db:8092/sse", timeout=30)
model_client = InternalMCPClient("http://model-mcp:8091/sse", timeout=30)

# Initialize components
memory_agent = MemoryAgent(storage=None, enable_intelligence=True)
streaming_agent = StreamingMemoryAgent(memory_agent, memory_event_stream)
hierarchical_types = HierarchicalMemoryType()

# Create orchestrator
orchestrator = MemoryOrchestrator(
    memory_agent=streaming_agent,  # Use streaming-enabled agent
    rag_client=rag_client,
    db_client=db_client,
    model_client=model_client
)

@mcp.tool(description="Store a memory with hierarchical classification")
async def store_memory(
    user_id: str,
    content: str,
    session_id: Optional[str] = None,
    memory_type: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> str:
    """
    Store memory with single responsibility
    """
    try:
        # Use hierarchical classification if type not provided
        if not memory_type:
            classification = hierarchical_types.classify(content, metadata)
            memory_type = classification.to_path()
            
            # Add classification to metadata
            if metadata is None:
                metadata = {}
            metadata["classification"] = classification.to_dict()
            metadata["importance"] = hierarchical_types.get_importance(classification)
        
        # Store using orchestrator
        result = await orchestrator.store_memory(
            user_id=user_id,
            content=content,
            session_id=session_id or f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            memory_type=memory_type,
            metadata=metadata
        )
        
        return json.dumps({
            "success": result.get("status") == "success",
            "memory_id": result.get("memory_id"),
            "memory_type": memory_type,
            "classification": metadata.get("classification"),
            "importance": result.get("importance"),
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error storing memory: {e}", exc_info=True)
        return json.dumps({
            "success": False,
            "error": str(e)
        })

@mcp.tool(description="Retrieve memories with enhanced search")
async def retrieve_memories(
    user_id: str,
    query: str,
    memory_types: Optional[List[str]] = None,
    session_id: Optional[str] = None,
    limit: int = 10,
    include_related: bool = True
) -> str:
    """
    Retrieve memories with single responsibility
    """
    try:
        # If memory types specified, expand with related types
        if memory_types and include_related:
            expanded_types = set(memory_types)
            for mem_type in memory_types:
                # Parse type path
                parts = mem_type.split('/')
                if len(parts) == 3:
                    classification = MemoryClassification(*parts, confidence=1.0)
                    related = hierarchical_types.get_related_types(classification)
                    expanded_types.update(related)
            memory_types = list(expanded_types)
        
        # Retrieve using orchestrator
        memories = await orchestrator.retrieve_memories(
            user_id=user_id,
            query=query,
            memory_types=memory_types,
            session_id=session_id,
            limit=limit
        )
        
        return json.dumps({
            "success": True,
            "memories": memories,
            "count": len(memories),
            "query": query,
            "searched_types": memory_types
        })
        
    except Exception as e:
        logger.error(f"Error retrieving memories: {e}", exc_info=True)
        return json.dumps({
            "success": False,
            "error": str(e),
            "memories": []
        })

@mcp.tool(description="Get contextual information for a message")
async def get_context(
    user_id: str,
    message: str,
    session_id: Optional[str] = None,
    context_size: int = 5
) -> str:
    """
    Get context with single responsibility
    """
    try:
        context = await orchestrator.get_context(
            user_id=user_id,
            current_message=message,
            session_id=session_id,
            context_size=context_size
        )
        
        return json.dumps({
            "success": True,
            "context": context,
            "message": message
        })
        
    except Exception as e:
        logger.error(f"Error getting context: {e}", exc_info=True)
        return json.dumps({
            "success": False,
            "error": str(e),
            "context": {}
        })

@mcp.tool(description="Generate response using context")
async def generate_contextual_response(
    user_id: str,
    prompt: str,
    session_id: Optional[str] = None,
    use_context: bool = True,
    model: str = "EXAONE-3.5-2.4B-Instruct"
) -> str:
    """
    Generate response with single responsibility
    """
    try:
        # Get context if requested
        context = {}
        if use_context:
            context = await orchestrator.get_context(
                user_id=user_id,
                current_message=prompt,
                session_id=session_id
            )
        
        # Generate response
        response = await orchestrator.generate_response(
            prompt=prompt,
            context=context,
            model=model
        )
        
        # Optionally store the interaction
        if session_id:
            # Store user message
            await orchestrator.store_memory(
                user_id=user_id,
                content=f"User: {prompt}",
                session_id=session_id,
                memory_type="temporal/conversation/question"
            )
            
            # Store assistant response
            await orchestrator.store_memory(
                user_id=user_id,
                content=f"Assistant: {response[:500]}",
                session_id=session_id,
                memory_type="temporal/conversation/response"
            )
        
        return json.dumps({
            "success": True,
            "response": response,
            "context_used": use_context,
            "context_size": context.get("total_context", 0) if context else 0
        })
        
    except Exception as e:
        logger.error(f"Error generating response: {e}", exc_info=True)
        return json.dumps({
            "success": False,
            "error": str(e),
            "response": ""
        })

@mcp.tool(description="Analyze content and classify memory type")
async def analyze_content(
    content: str,
    context: Optional[Dict[str, Any]] = None
) -> str:
    """
    Analyze content with hierarchical classification
    """
    try:
        # Get hierarchical classification
        classification = hierarchical_types.classify(content, context)
        
        # Get storage strategy
        strategy = hierarchical_types.get_storage_strategy(classification)
        
        # Get importance
        importance = hierarchical_types.get_importance(classification)
        
        # Get related types
        related_types = hierarchical_types.get_related_types(classification)
        
        return json.dumps({
            "success": True,
            "classification": classification.to_dict(),
            "importance": importance,
            "storage_strategy": strategy,
            "related_types": related_types
        })
        
    except Exception as e:
        logger.error(f"Error analyzing content: {e}", exc_info=True)
        return json.dumps({
            "success": False,
            "error": str(e)
        })

@mcp.tool(description="Get memory statistics with hierarchy")
async def get_memory_stats(
    user_id: str,
    session_id: Optional[str] = None,
    group_by_hierarchy: bool = True
) -> str:
    """
    Get statistics with hierarchical grouping
    """
    try:
        # Get basic stats from memory agent
        stats = await memory_agent.storage.get_memory_stats(user_id, session_id)
        
        # Add hierarchical grouping
        if group_by_hierarchy and "type_distribution" in stats:
            hierarchy_stats = {
                "personal": {},
                "knowledge": {},
                "temporal": {}
            }
            
            for mem_type, count in stats["type_distribution"].items():
                # Try to parse as hierarchical type
                if "/" in mem_type:
                    parts = mem_type.split("/")
                    if parts[0] in hierarchy_stats:
                        if parts[1] not in hierarchy_stats[parts[0]]:
                            hierarchy_stats[parts[0]][parts[1]] = 0
                        hierarchy_stats[parts[0]][parts[1]] += count
            
            stats["hierarchy_distribution"] = hierarchy_stats
        
        # Add streaming stats
        stats["streaming_stats"] = memory_event_stream.get_stats()
        
        return json.dumps({
            "success": True,
            "stats": stats,
            "user_id": user_id,
            "session_id": session_id
        })
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}", exc_info=True)
        return json.dumps({
            "success": False,
            "error": str(e),
            "stats": {}
        })

# Initialize
logger.info("Refactored Memory Orchestrator tools loaded")