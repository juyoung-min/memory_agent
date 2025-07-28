import json
import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid

from mcp_instance import mcp
from src.clients import InternalModelClient, InternalDBClient
from src.config import get_config

# Initialize configuration
config = get_config()
logger = logging.getLogger(__name__)

# Initialize clients once at module level
model_client = InternalModelClient(config.model_mcp_url, timeout=config.model_timeout)
db_client = InternalDBClient(config.db_mcp_url, timeout=config.db_timeout)

def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """Split text into overlapping chunks"""
    chunks = []
    start = 0
    text_length = len(text)
    
    while start < text_length:
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - overlap
    
    return chunks

@mcp.tool(description="Save document with automatic embedding generation")
async def rag_save_document(content: str, namespace: str = 'default', document_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None, chunk: bool = True, collection: Optional[str] = None) -> str:
    """
    Save a document by generating embeddings and storing in vector database.
    Orchestrates Model-MCP for embedding generation and DB-MCP for storage.
    """
    
    # Set defaults
    if document_id is None:
        document_id = str(uuid.uuid4())
    if metadata is None:
        metadata = {}
    if collection is None:
        collection = config.default_collection
    chunk_content = chunk
    
    if not content:
        return json.dumps({
            "success": False,
            "error": "Content is required",
            "error_type": "ValidationError"
        })
    
    try:
        # Prepare metadata
        base_metadata = {
            "namespace": namespace,
            "document_id": document_id,
            "timestamp": datetime.utcnow().isoformat(),
            **metadata
        }
        
        if chunk_content and len(content) > config.chunk_size:
            # Chunk the document
            chunks = chunk_text(content, config.chunk_size, config.chunk_overlap)
            logger.info(f"Document chunked into {len(chunks)} pieces")
            
            # Generate embeddings for all chunks
            logger.info("Generating embeddings for chunks...")
            embedding_results = await model_client.batch_generate_embeddings(chunks)
            
            if not embedding_results.get("success"):
                return json.dumps({
                    "success": False,
                    "error": "Failed to generate embeddings",
                    "details": embedding_results.get("errors")
                })
            
            # Prepare batch storage
            items = []
            for i, (chunk, embedding) in enumerate(zip(chunks, embedding_results["embeddings"])):
                if embedding:  # Skip failed embeddings
                    chunk_metadata = {
                        **base_metadata,
                        "chunk_index": i,
                        "total_chunks": len(chunks)
                    }
                    items.append({
                        "id": f"{document_id}_chunk_{i}",
                        "content": chunk,
                        "vector": embedding,
                        "metadata": chunk_metadata
                    })
            
            # Store all chunks
            logger.info(f"Storing {len(items)} chunks in database...")
            storage_result = await db_client.batch_store_vectors(collection, items)
            
            return json.dumps({
                "success": storage_result.get("success", False),
                "document_id": document_id,
                "chunks_stored": len(items),
                "total_chunks": len(chunks),
                "errors": storage_result.get("errors")
            })
            
        else:
            # Single document without chunking
            logger.info("Generating embedding for document...")
            embedding_result = await model_client.generate_embedding(content)
            
            if not embedding_result.get("success"):
                return json.dumps({
                    "success": False,
                    "error": "Failed to generate embedding",
                    "details": embedding_result.get("error")
                })
            
            # Store the document
            logger.info("Storing document in database...")
            storage_result = await db_client.store_vector(
                table=collection,
                content=content,
                vector=embedding_result["embedding"],
                metadata=base_metadata
            )
            
            return json.dumps({
                "success": storage_result.get("success", False),
                "document_id": document_id,
                "message": "Document stored successfully" if storage_result.get("success") else "Storage failed",
                "errors": storage_result.get("error")
            })
            
    except Exception as e:
        logger.error(f"Failed to save document: {e}", exc_info=True)
        return json.dumps({
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        })

@mcp.tool(description="Semantic search across documents")
async def rag_search(query: str, namespace: Optional[str] = None, limit: Optional[int] = None, similarity_threshold: Optional[float] = None, collection: Optional[str] = None, include_content: bool = True, filters: Optional[Dict[str, Any]] = None) -> str:
    """
    Search for documents using semantic similarity.
    Generates query embedding and searches in vector database.
    """
    
    # Set defaults
    if limit is None:
        limit = config.default_search_limit
    if similarity_threshold is None:
        threshold = config.default_similarity_threshold
    else:
        threshold = similarity_threshold
    if collection is None:
        collection = config.default_collection
    if filters is None:
        filters = {}
    
    if not query:
        return json.dumps({
            "success": False,
            "error": "Query is required",
            "error_type": "ValidationError"
        })
    
    try:
        # Generate query embedding
        logger.info("Generating embedding for search query...")
        embedding_result = await model_client.generate_embedding(query)
        
        if not embedding_result.get("success"):
            return json.dumps({
                "success": False,
                "error": "Failed to generate query embedding",
                "details": embedding_result.get("error")
            })
        
        # Add namespace filter if provided
        if namespace:
            filters["namespace"] = namespace
        
        # Search in database
        logger.info(f"Searching in collection: {collection}")
        search_result = await db_client.search_vectors(
            table=collection,
            query_vector=embedding_result["embedding"],
            limit=limit,
            threshold=threshold,
            filters=filters
        )
        
        if not search_result.get("success", False):
            return json.dumps({
                "success": False,
                "error": "Search failed",
                "details": search_result.get("error")
            })
        
        # Process results
        results = search_result.get("results", [])
        
        # Optionally remove content for lighter response
        if not include_content:
            for result in results:
                result.pop("content", None)
        
        return json.dumps({
            "success": True,
            "query": query,
            "results": results,
            "count": len(results),
            "limit": limit,
            "threshold": threshold
        })
        
    except Exception as e:
        logger.error(f"Search failed: {e}", exc_info=True)
        return json.dumps({
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        })

@mcp.tool(description="Generate answer using RAG")
async def rag_generate_answer(question: str, namespace: Optional[str] = None, search_limit: int = 5, collection: Optional[str] = None, system_prompt: Optional[str] = None, max_tokens: int = 1024) -> str:
    """
    Generate an answer using retrieval-augmented generation.
    Searches for relevant context and generates response using LLM.
    """
    
    logger.error("===== RAG_GENERATE_ANSWER CALLED! =====")
    logger.error(f"Question: {question}")
    
    # Set defaults
    if collection is None:
        collection = config.default_collection
    if system_prompt is None:
        system_prompt = "You are a helpful assistant. Use the provided context to answer the question."
    
    if not question:
        return json.dumps({
            "success": False,
            "error": "Question is required",
            "error_type": "ValidationError"
        })
    
    try:
        # Step 1: Search for relevant context
        logger.info("Searching for relevant context...")
        search_response = await rag_search(
            query=question,
            namespace=namespace,
            limit=search_limit,
            collection=collection,
            include_content=True
        )
        
        search_data = json.loads(search_response)
        if not search_data.get("success"):
            return json.dumps({
                "success": False,
                "error": "Failed to retrieve context",
                "details": search_data.get("error")
            })
        
        # Step 2: Prepare context from search results
        contexts = []
        for result in search_data.get("results", []):
            content = result.get("content", "")
            similarity = result.get("similarity", 0)
            contexts.append(f"[Relevance: {similarity:.2f}] {content}")
        
        context_text = "\n\n".join(contexts)
        
        # Step 3: Generate answer using LLM
        prompt = f"""{system_prompt}

Context:
{context_text}

Question: {question}

Answer:"""
        
        logger.info("Generating answer using LLM...")
        llm_response = await model_client.generate_response(
            prompt=prompt,
            model_name=config.default_llm_model,
            max_tokens=max_tokens
        )
        
        logger.info(f"===== ORCHESTRATOR: Received LLM response back =====")
        
        # Log the full LLM response for debugging
        logger.info(f"LLM response type: {type(llm_response)}")
        logger.info(f"LLM response keys: {list(llm_response.keys()) if isinstance(llm_response, dict) else 'Not a dict'}")
        
        # Check for error status first
        if isinstance(llm_response, dict) and llm_response.get("status") == "error":
            logger.error(f"LLM returned error: {llm_response.get('message')}")
            return json.dumps({
                "success": False,
                "error": "Failed to generate answer",
                "details": llm_response.get("message")
            })
        
        # Extract answer from LLM response
        answer = ""
        
        logger.info(f"Starting answer extraction")
        
        try:
            # Direct extraction from OpenAI format
            if isinstance(llm_response, dict) and "choices" in llm_response:
                choices = llm_response.get("choices", [])
                if choices and len(choices) > 0:
                    choice = choices[0]
                    if isinstance(choice, dict) and "message" in choice:
                        message = choice.get("message", {})
                        if isinstance(message, dict) and "content" in message:
                            answer = message.get("content", "")
                            logger.info(f"Successfully extracted answer: '{answer}'")
                        else:
                            logger.warning(f"Message missing content field: {message}")
                    else:
                        logger.warning(f"Choice missing message field: {choice}")
                else:
                    logger.warning("No choices in response")
            else:
                logger.warning(f"Response not in expected format")
                
            if not answer:
                logger.error(f"Failed to extract answer. Full response: {json.dumps(llm_response, indent=2)[:500]}")
        except Exception as e:
            logger.error(f"Exception during answer extraction: {str(e)}", exc_info=True)
        
        logger.info(f"===== ORCHESTRATOR: Final answer before returning: '{answer}' =====")
        
        result = {
            "success": True,
            "question": question,
            "answer": answer,
            "context_count": len(contexts),
            "model": config.default_llm_model
        }
        
        logger.info(f"===== ORCHESTRATOR: Returning result: {json.dumps(result)} =====")
        return json.dumps(result)
        
    except Exception as e:
        logger.error(f"Failed to generate answer: {e}", exc_info=True)
        return json.dumps({
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        })

@mcp.tool(description="Simple test tool")
async def test_tool() -> str:
    """Test tool to verify changes are being deployed"""
    return json.dumps({
        "success": True,
        "message": "Test tool is working!",
        "timestamp": datetime.utcnow().isoformat()
    })

@mcp.tool(description="Debug answer generation")
async def debug_answer_generation() -> str:
    """Debug version of answer generation"""
    try:
        # Step 1: Test model client
        logger.info("Debug: Testing model client...")
        
        test_response = await model_client.generate_response(
            prompt="Say 'Hello, this is a test response'",
            model_name=config.default_llm_model,
            max_tokens=50
        )
        
        logger.info(f"Debug: Got response: {test_response}")
        
        # Return the raw response for debugging
        return json.dumps({
            "success": True,
            "raw_response": test_response,
            "response_type": str(type(test_response)),
            "response_keys": list(test_response.keys()) if isinstance(test_response, dict) else None
        })
        
    except Exception as e:
        logger.error(f"Debug error: {e}", exc_info=True)
        return json.dumps({
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        })

@mcp.tool(description="Delete document and its embeddings")
async def rag_delete_document(document_id: str, collection: Optional[str] = None) -> str:
    """Delete a document and all its chunks from the vector database"""
    
    if collection is None:
        collection = config.default_collection
    
    if not document_id:
        return json.dumps({
            "success": False,
            "error": "Document ID is required",
            "error_type": "ValidationError"
        })
    
    try:
        # Search for all chunks of the document
        search_result = await db_client.search_vectors(
            table=collection,
            query_vector=[0] * 1536,  # Dummy vector
            limit=1000,  # Get all chunks
            filters={"document_id": document_id}
        )
        
        if not search_result.get("success"):
            return json.dumps({
                "success": False,
                "error": "Failed to find document chunks",
                "details": search_result.get("error")
            })
        
        # Extract IDs to delete
        ids_to_delete = [r.get("id") for r in search_result.get("results", [])]
        
        if not ids_to_delete:
            return json.dumps({
                "success": True,
                "message": "No documents found to delete",
                "document_id": document_id
            })
        
        # Delete all chunks
        delete_result = await db_client.delete_vectors(collection, ids_to_delete)
        
        return json.dumps({
            "success": delete_result.get("success", False),
            "document_id": document_id,
            "chunks_deleted": len(ids_to_delete),
            "errors": delete_result.get("error")
        })
        
    except Exception as e:
        logger.error(f"Failed to delete document: {e}", exc_info=True)
        return json.dumps({
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        })