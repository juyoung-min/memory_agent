# embedding_utils.py

"""
Embedding utilities for dynamic dimension handling
"""

import logging
from typing import Dict, Any, Optional, Tuple
from src.clients import InternalMCPClient
from .vector_index_optimizer import MemoryVectorIndexOptimizer, MemorySearchOptimizer

logger = logging.getLogger(__name__)

# Cache for model dimensions
_model_dimensions_cache: Dict[str, int] = {
    # Known model dimensions
    "bge-m3": 1024,
    "text-embedding-ada-002": 1536,
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
}

async def get_embedding_dimension(model_name: str, rag_client: InternalMCPClient) -> int:
    """
    Get the embedding dimension for a specific model.
    First checks cache, then tries to get from RAG-MCP.
    """
    # Check cache first
    if model_name in _model_dimensions_cache:
        return _model_dimensions_cache[model_name]
    
    try:
        # Try to get a test embedding from RAG-MCP to determine dimension
        logger.info(f"Determining embedding dimension for model: {model_name}")
        
        # RAG-MCP should handle embeddings, not model-mcp directly
        test_response = await rag_client.call_tool(
            "rag_generate_embedding",
            {
                "text": "test",
                "model": model_name
            }
        )
        
        if test_response.get("success") and test_response.get("embedding"):
            dimension = len(test_response["embedding"])
            _model_dimensions_cache[model_name] = dimension
            logger.info(f"Detected dimension {dimension} for model {model_name}")
            return dimension
            
    except Exception as e:
        logger.error(f"Error getting embedding dimension: {e}")
    
    # Default fallback
    logger.warning(f"Could not determine dimension for {model_name}, using default 1024")
    return 1024

async def ensure_table_with_dimension(
    db_client: InternalMCPClient,
    table_name: str,
    dimension: int,
    additional_columns: Optional[Dict[str, str]] = None
) -> bool:
    """
    Ensure a table exists with the correct vector dimension.
    Creates or recreates the table if dimension mismatch.
    """
    try:
        # Check if table exists and get current dimension
        check_result = await db_client.call_tool(
            "db_execute_query",
            {
                "query": f"""
                    SELECT 
                        column_name,
                        udt_name,
                        character_maximum_length,
                        numeric_precision
                    FROM information_schema.columns 
                    WHERE table_name = %s AND column_name = 'embedding'
                """,
                "params": [table_name]
            }
        )
        
        needs_recreation = False
        if check_result.get("success") and check_result.get("rows"):
            # Table exists, check dimension
            # For vector type, we need to check the type modifier
            dim_check = await db_client.call_tool(
                "db_execute_query",
                {
                    "query": f"""
                        SELECT 
                            pg_attribute.atttypmod 
                        FROM pg_attribute 
                        JOIN pg_class ON pg_class.oid = pg_attribute.attrelid 
                        WHERE pg_class.relname = %s 
                        AND pg_attribute.attname = 'embedding'
                    """,
                    "params": [table_name]
                }
            )
            
            if dim_check.get("success") and dim_check.get("rows"):
                # atttypmod for vector is dimension + 4
                current_dim = dim_check["rows"][0][0] - 4 if dim_check["rows"][0][0] else None
                if current_dim != dimension:
                    logger.warning(f"Table {table_name} has dimension {current_dim}, need {dimension}")
                    needs_recreation = True
        else:
            # Table doesn't exist
            needs_recreation = True
        
        if needs_recreation:
            logger.info(f"Creating table {table_name} with dimension {dimension}")
            
            # Build column definitions
            columns = [
                "id TEXT PRIMARY KEY",
                "content TEXT NOT NULL",
                f"embedding vector({dimension})",
                "metadata JSONB DEFAULT '{}'",
                "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                "updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
            ]
            
            # Add any additional columns
            if additional_columns:
                for col_name, col_def in additional_columns.items():
                    columns.append(f"{col_name} {col_def}")
            
            # Drop and recreate table
            await db_client.call_tool(
                "db_execute_query",
                {
                    "query": f"DROP TABLE IF EXISTS {table_name} CASCADE"
                }
            )
            
            create_query = f"""
                CREATE TABLE {table_name} (
                    {', '.join(columns)}
                )
            """
            
            create_result = await db_client.call_tool(
                "db_execute_query",
                {
                    "query": create_query
                }
            )
            
            if create_result.get("success"):
                # Create basic indexes first (non-vector)
                basic_indexes = [
                    f"CREATE INDEX idx_{table_name}_metadata ON {table_name} USING gin (metadata)",
                    f"CREATE INDEX idx_{table_name}_created_at ON {table_name} (created_at DESC)"
                ]
                
                # Add user_id index if it's a column
                if "user_id" in additional_columns:
                    basic_indexes.append(f"CREATE INDEX idx_{table_name}_user_id ON {table_name} (user_id)")
                
                for index_query in basic_indexes:
                    await db_client.call_tool(
                        "db_execute_query",
                        {"query": index_query}
                    )
                
                # Use optimizer for vector index
                optimizer = MemoryVectorIndexOptimizer(db_client)
                optimize_result = await optimizer.optimize_memory_index(table_name, force=True)
                
                if optimize_result.get("optimized"):
                    logger.info(f"Successfully created optimized index for {table_name}: {optimize_result.get('strategy', {}).get('type', 'unknown')}")
                else:
                    # Fallback to basic IVFFlat if optimization fails
                    logger.warning(f"Optimization failed, creating basic index: {optimize_result.get('error', 'Unknown error')}")
                    await db_client.call_tool(
                        "db_execute_query",
                        {
                            "query": f"CREATE INDEX idx_{table_name}_embedding ON {table_name} USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
                        }
                    )
                
                logger.info(f"Successfully created table {table_name} with dimension {dimension}")
                return True
            else:
                logger.error(f"Failed to create table {table_name}")
                return False
        else:
            logger.info(f"Table {table_name} already has correct dimension {dimension}")
            return True
            
    except Exception as e:
        logger.error(f"Error ensuring table {table_name}: {e}")
        return False

async def get_embedding_from_rag(
    rag_client: InternalMCPClient,
    text: str,
    model: str = "bge-m3"
) -> Tuple[Optional[list], int]:
    """
    Get embedding from RAG-MCP (which internally uses model-mcp).
    Returns tuple of (embedding, dimension).
    """
    try:
        response = await rag_client.call_tool(
            "rag_generate_embedding",
            {
                "text": text,
                "model": model
            }
        )
        
        if response.get("success") and response.get("embedding"):
            embedding = response["embedding"]
            dimension = len(embedding)
            return embedding, dimension
        else:
            logger.error(f"Failed to generate embedding: {response}")
            return None, 0
            
    except Exception as e:
        logger.error(f"Error generating embedding: {e}")
        return None, 0