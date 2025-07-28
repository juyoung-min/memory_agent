"""
Memory Agent Orchestrator Tool with Enhanced Intelligence
Integrates memory management with RAG-MCP using enhanced content processing
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
from src.memory_agent.enhanced_intelligence import EnhancedMemoryIntelligence, ProcessedContent
from src.storage_strategy import StorageStrategyDeterminer, StorageLocation
from src.config import get_config
from src.embedding_utils import get_embedding_dimension, ensure_table_with_dimension, get_embedding_from_rag
from src.vector_index_optimizer import MemorySearchOptimizer

# Initialize configuration
config = get_config()
logger = logging.getLogger(__name__)

# Initialize clients
rag_client = InternalMCPClient("http://mcp-rag:8093/sse", timeout=30)
db_client = InternalMCPClient("http://mcp-db:8092/sse", timeout=30)
model_client = InternalMCPClient("http://model-mcp:8091/sse", timeout=30)

# Initialize Enhanced Intelligence
enhanced_intelligence = EnhancedMemoryIntelligence()
storage_strategy_determiner = StorageStrategyDeterminer()

# Initialize Memory Agent with storage
memory_agent = MemoryAgent(
    storage=None,  # Will use DB-MCP for storage
    enable_intelligence=True
)

# Replace the basic intelligence with enhanced intelligence
memory_agent.intelligence = enhanced_intelligence

@mcp.tool(description="Process and store user message with intelligent content processing")
async def process_message_enhanced(
    user_id: str,
    message: str,
    session_id: str,
    memory_type: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> str:
    """
    Process and store user message with enhanced intelligent memory management
    
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
        logger.info(f"Processing message with enhanced intelligence for user {user_id}: {message[:50]}...")
        
        # Step 1: Analyze content with enhanced intelligence
        if not memory_type:
            # Auto-classify
            detected_type = memory_agent.intelligence.extract_memory_type(message, metadata or {})
        else:
            # Use provided type
            detected_type = MemoryType(memory_type)
        
        # Step 2: Process content for intelligent storage
        processed_content = enhanced_intelligence.process_content_for_storage(
            content=message,
            memory_type=detected_type,
            context={
                "user_id": user_id,
                "session_id": session_id,
                "timestamp": datetime.utcnow().isoformat(),
                **(metadata or {})
            }
        )
        
        # Step 3: Check if content should be stored
        if not processed_content.should_store:
            logger.info(f"Content not significant enough to store: {message[:50]}...")
            return json.dumps({
                "success": True,
                "stored": False,
                "reason": "Content not significant for storage",
                "processed": {
                    "keywords": processed_content.keywords,
                    "entities": processed_content.extracted_entities
                }
            })
        
        # Step 4: Determine storage strategy
        storage_strategy = storage_strategy_determiner.determine_strategy(
            memory_type=detected_type.value,
            importance=processed_content.importance,
            content_size=len(message),
            access_pattern="frequent" if detected_type == MemoryType.CONVERSATION else None
        )
        
        # Step 5: Store processed content based on strategy
        storage_content = processed_content.structured_content
        
        # Store in memory agent
        memory_result = await memory_agent.add_memory(
            user_id=user_id,
            session_id=session_id,
            content=storage_content,  # Use processed content
            memory_type=detected_type.value,
            importance=processed_content.importance,
            metadata={
                "source": "user_message",
                "timestamp": datetime.utcnow().isoformat(),
                "processed": True,
                "storage_format": processed_content.storage_format,
                "keywords": processed_content.keywords,
                "entities": processed_content.extracted_entities,
                "original_content": message,  # Keep original for reference
                **(processed_content.metadata),
                **(metadata or {})
            }
        )
        
        # Step 6: Execute storage strategy
        rag_stored = False
        if storage_strategy.includes_rag:
            logger.info(f"Storing in RAG-MCP as per strategy: {storage_strategy.to_dict()}")
            
            # Prepare content for RAG storage
            rag_content = processed_content.summary if processed_content.summary else storage_content
            
            rag_store_result = await rag_client.call_tool(
                "rag_save_document",
                {
                    "content": rag_content,
                    "namespace": f"{user_id}_{detected_type.value}",
                    "document_id": memory_result.get("memory_id"),
                    "metadata": {
                        "user_id": user_id,
                        "session_id": session_id,
                        "memory_type": detected_type.value,
                        "importance": processed_content.importance,
                        "keywords": processed_content.keywords,
                        "timestamp": datetime.utcnow().isoformat(),
                        "entities": [e["value"] for e in processed_content.extracted_entities]
                    },
                    "chunk": storage_strategy.compression_enabled and len(rag_content) > 1000
                }
            )
            
            rag_stored = rag_store_result.get("success", False)
        
        return json.dumps({
            "success": memory_result["status"] == "success",
            "memory_id": memory_result.get("memory_id"),
            "memory_type": detected_type.value,
            "importance": processed_content.importance,
            "processed": {
                "storage_format": processed_content.storage_format,
                "keywords": processed_content.keywords,
                "entities": processed_content.extracted_entities,
                "summary": processed_content.summary
            },
            "storage_strategy": storage_strategy.to_dict(),
            "rag_stored": rag_stored,
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error in process_message_enhanced: {e}", exc_info=True)
        return json.dumps({
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        })

@mcp.tool(description="Process user prompt with enhanced intelligence and automatic memory management")
async def process_user_prompt_enhanced(
    user_id: str,
    prompt: str,
    session_id: str,
    auto_store: bool = True,
    generate_response: bool = True
) -> str:
    """
    Handle user prompt with enhanced intelligent memory operations
    
    This tool:
    1. Searches relevant memories for context
    2. Processes and stores the prompt with enhanced intelligence
    3. Generates a response using context
    4. Stores the processed response
    
    Args:
        user_id: User identifier
        prompt: User's prompt/message
        session_id: Session identifier
        auto_store: Whether to automatically store memories
        generate_response: Whether to generate a response
    """
    try:
        logger.info(f"Processing prompt with enhanced intelligence for user {user_id}: {prompt[:50]}...")
        
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
        
        # Step 2: Analyze and process the prompt with enhanced intelligence
        memory_analysis = memory_agent.intelligence.extract_memory_type(prompt, {})
        
        # Process content
        context_info = {
            "user_id": user_id,
            "session_id": session_id,
            "has_context": len(conv_results) + len(mem_results) > 0,
            "context_count": len(conv_results) + len(mem_results),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        processed_content = enhanced_intelligence.process_content_for_storage(
            content=prompt,
            memory_type=memory_analysis,
            context=context_info
        )
        
        # Step 3: Store the processed prompt if appropriate
        stored_memory = None
        if auto_store and processed_content.should_store:
            # Determine storage strategy
            storage_strategy = storage_strategy_determiner.determine_strategy(
                memory_type=memory_analysis.value,
                importance=processed_content.importance,
                content_size=len(prompt)
            )
            
            # Store using enhanced processing
            store_result = await process_message_enhanced(
                user_id=user_id,
                message=prompt,
                session_id=session_id,
                memory_type=memory_analysis.value,
                metadata={
                    "role": "user",
                    "context_aware": True,
                    "processed_content": processed_content.metadata
                }
            )
            
            stored_memory = json.loads(store_result)
        
        # Step 4: Generate response if requested
        response_content = ""
        if generate_response:
            # Build context from memories with structure
            context_parts = []
            
            # Add conversation context
            if conv_results:
                context_parts.append("=== Recent Conversation History ===")
                for i, conv in enumerate(conv_results[:5]):
                    context_parts.append(f"{i+1}. {conv['content']}")
                context_parts.append("")
            
            # Add structured memory context
            if mem_results:
                context_parts.append("=== User Information ===")
                # Group by type
                by_type = {}
                for mem in mem_results:
                    mem_type = mem.get('type', 'info')
                    if mem_type not in by_type:
                        by_type[mem_type] = []
                    by_type[mem_type].append(mem['content'])
                
                for mem_type, contents in by_type.items():
                    context_parts.append(f"[{mem_type.upper()}]")
                    for content in contents[:2]:  # Limit per type
                        context_parts.append(f"  • {content}")
                context_parts.append("")
            
            # Add processed prompt information
            if processed_content.keywords:
                context_parts.append(f"=== Current Topic Keywords: {', '.join(processed_content.keywords[:5])} ===")
                context_parts.append("")
            
            full_context = "\n".join(context_parts) if context_parts else ""
            
            # Generate response with enhanced prompt
            generation_prompt = f"""You are a helpful assistant with access to the user's conversation history and information.

{full_context}
Current User Message: {prompt}

Detected Intent: {memory_analysis.value}
Importance: {processed_content.importance}/10

Instructions:
1. Use the context above to provide personalized, relevant responses
2. If the user asks about previous messages, refer to the Recent Conversation History
3. Answer in the same language as the user
4. Be specific and accurate when recalling information
5. Consider the detected intent and importance when formulating your response

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
            
            # Process and store the response
            if auto_store:
                # Process response for storage
                response_processed = enhanced_intelligence.process_content_for_storage(
                    content=response_content,
                    memory_type=MemoryType.CONVERSATION,
                    context={
                        "role": "assistant",
                        "in_response_to": prompt,
                        "user_id": user_id,
                        "session_id": session_id
                    }
                )
                
                if response_processed.should_store:
                    await process_message_enhanced(
                        user_id=user_id,
                        message=response_content[:500],
                        session_id=session_id,
                        memory_type="conversation",
                        metadata={
                            "role": "assistant",
                            "in_response_to_id": stored_memory.get("memory_id") if stored_memory else None,
                            "summary": response_processed.summary
                        }
                    )
        
        # Step 5: Return comprehensive result
        return json.dumps({
            "success": True,
            "response": response_content,
            "processing_details": {
                "prompt_analysis": {
                    "detected_type": memory_analysis.value,
                    "importance": processed_content.importance,
                    "keywords": processed_content.keywords,
                    "entities": processed_content.extracted_entities,
                    "should_store": processed_content.should_store,
                    "storage_format": processed_content.storage_format
                },
                "context_found": {
                    "conversations": len(conv_results),
                    "memories": len(mem_results),
                    "total_context": len(conv_results) + len(mem_results)
                },
                "storage_details": stored_memory if stored_memory else None
            },
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error processing user prompt with enhanced intelligence: {e}", exc_info=True)
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
    """
    try:
        # Search conversation memories from database
        logger.info(f"Retrieving conversation history for user {user_id} from database")
        
        # Use enhanced search with importance filtering
        search_result = await search_user_memories(
            user_id=user_id,
            query=query,
            session_id=session_id,
            limit=limit,
            memory_types=["conversation"],
            importance_threshold=None  # Include all conversations
        )
        
        search_data = json.loads(search_result)
        
        if not search_data.get("success"):
            return json.dumps({
                "success": False,
                "error": "Failed to search conversation history",
                "conversations": []
            })
        
        # Format results with enhanced metadata
        conversations = []
        for mem in search_data.get("memories", []):
            conversations.append({
                "content": mem.get("content"),
                "similarity": mem.get("similarity"),
                "session_id": mem.get("session_id"),
                "timestamp": mem.get("timestamp"),
                "memory_id": mem.get("id"),
                "importance": mem.get("importance", 5.0),
                "keywords": mem.get("keywords", []),
                "entities": mem.get("entities", []),
                "storage_format": mem.get("storage_format", "full")
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

@mcp.tool(description="Search user memories with enhanced filtering")
async def search_user_memories(
    user_id: str,
    query: str,
    session_id: Optional[str] = None,
    limit: int = 10,
    memory_types: Optional[List[str]] = None,
    importance_threshold: Optional[float] = None
) -> str:
    """
    Search user's memories using semantic similarity with enhanced filtering
    """
    try:
        # Get embedding model from config
        embedding_model = config.intelligence.language_models.get("embedding", "bge-m3")
        
        # Ensure table exists with correct dimension
        dimension = await get_embedding_dimension(embedding_model, rag_client)
        table_created = await ensure_table_with_dimension(
            db_client,
            "user_memories",
            dimension,
            additional_columns={
                "user_id": "TEXT NOT NULL",
                "session_id": "TEXT",
                "memory_type": "TEXT",
                "importance": "REAL",
                "keywords": "TEXT[]",
                "storage_format": "TEXT"
            }
        )
        
        if not table_created:
            logger.warning("Could not ensure user_memories table exists")
        
        # Generate embedding through RAG-MCP
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
        if importance_threshold:
            filters["importance"] = {"$gte": importance_threshold}
        
        # Use optimized search
        search_optimizer = MemorySearchOptimizer(db_client)
        
        # Determine optimization based on query type
        optimize_for = "balanced"
        if memory_types and len(memory_types) == 1 and memory_types[0] == "conversation":
            # Conversations need accuracy for context
            optimize_for = "accuracy"
        elif importance_threshold and importance_threshold >= 8:
            # High importance queries need accuracy
            optimize_for = "accuracy"
        elif limit > 20:
            # Large result sets can trade accuracy for speed
            optimize_for = "speed"
        
        # Perform optimized search
        search_result = await search_optimizer.optimized_search(
            table_name="user_memories",
            query_vector=query_vector,
            filters=filters,
            limit=limit,
            optimize_for=optimize_for
        )
        
        if not search_result.get("success"):
            # Fallback to standard search if optimization fails
            logger.warning("Optimized search failed, falling back to standard search")
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
            performance_info = None
        else:
            memories = search_result.get("results", [])
            performance_info = search_result.get("performance")
        
        # Enhance results with metadata
        for memory in memories:
            # Parse keywords and entities if stored as JSON
            if "keywords" in memory and isinstance(memory["keywords"], str):
                try:
                    memory["keywords"] = json.loads(memory["keywords"])
                except:
                    pass
        
        result = {
            "success": True,
            "memories": memories,
            "count": len(memories),
            "embedding_dimension": actual_dimension,
            "filters_applied": filters
        }
        
        # Add performance info if available
        if performance_info:
            result["performance"] = performance_info
        
        return json.dumps(result)
        
    except Exception as e:
        logger.error(f"Error searching memories: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "memories": []
        })

@mcp.tool(description="Analyze content and provide storage recommendations")
async def analyze_content_for_storage(
    content: str,
    user_id: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None
) -> str:
    """
    Analyze content and provide detailed storage recommendations
    """
    try:
        # Auto-detect memory type
        detected_type = memory_agent.intelligence.extract_memory_type(content, context or {})
        
        # Process content
        processed = enhanced_intelligence.process_content_for_storage(
            content=content,
            memory_type=detected_type,
            context=context or {}
        )
        
        # Get storage strategy
        strategy = storage_strategy_determiner.determine_strategy(
            memory_type=detected_type.value,
            importance=processed.importance,
            content_size=len(content)
        )
        
        # Calculate storage cost
        storage_cost = storage_strategy_determiner.get_storage_cost(strategy, len(content))
        
        return json.dumps({
            "success": True,
            "analysis": {
                "detected_type": detected_type.value,
                "importance": processed.importance,
                "should_store": processed.should_store,
                "storage_format": processed.storage_format,
                "keywords": processed.keywords,
                "entities": processed.extracted_entities,
                "summary": processed.summary
            },
            "storage_recommendation": {
                "strategy": strategy.to_dict(),
                "estimated_cost": storage_cost,
                "rationale": f"Content classified as {detected_type.value} with importance {processed.importance}/10"
            },
            "processed_content": {
                "structured": processed.structured_content[:200] + "..." if len(processed.structured_content) > 200 else processed.structured_content,
                "metadata": processed.metadata
            }
        })
        
    except Exception as e:
        logger.error(f"Error analyzing content: {e}", exc_info=True)
        return json.dumps({
            "success": False,
            "error": str(e)
        })

# Initialize on module load
logger.info("Enhanced Memory Agent Orchestrator tools loaded successfully")