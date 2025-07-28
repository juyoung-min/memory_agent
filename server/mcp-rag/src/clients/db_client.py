from .base_client import InternalMCPClient
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class InternalDBClient(InternalMCPClient):
    """Internal client for server-to-server communication with DB-MCP"""
    
    async def store_vector(self, table: str, content: str, vector: List[float], 
                          metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Store a vector with metadata in the database"""
        
        logger.info(f"Storing vector in table: {table}")
        
        response = await self.call_tool(
            "db_store_vector",
            {
                "table": table,
                "content": content,
                "vector": vector,
                "metadata": metadata or {}
            }
        )
        
        return response
    
    async def batch_store_vectors(self, table: str, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Store multiple vectors in batch"""
        
        logger.info(f"Storing {len(items)} vectors in table: {table}")
        
        response = await self.call_tool(
            "db_batch_store_vectors",
            {
                "table": table,
                "items": items
            }
        )
        
        return response
    
    async def search_vectors(self, table: str, query_vector: List[float], 
                           limit: int = 10, threshold: float = 0.7,
                           filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Search for similar vectors in the database"""
        
        logger.info(f"Searching vectors in table: {table} with limit: {limit}")
        
        response = await self.call_tool(
            "db_search_vectors",
            {
                "table": table,
                "query_vector": query_vector,
                "limit": limit,
                "similarity_threshold": threshold,
                "filters": filters or {}
            }
        )
        
        return response
    
    async def delete_vectors(self, table: str, ids: List[str]) -> Dict[str, Any]:
        """Delete vectors by IDs"""
        
        logger.info(f"Deleting {len(ids)} vectors from table: {table}")
        
        response = await self.call_tool(
            "db_delete_vectors",
            {
                "table": table,
                "ids": ids
            }
        )
        
        return response
    
    async def update_vector_metadata(self, table: str, id: str, 
                                   metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Update metadata for a vector"""
        
        logger.info(f"Updating metadata for vector {id} in table: {table}")
        
        response = await self.call_tool(
            "db_update_metadata",
            {
                "table": table,
                "id": id,
                "metadata": metadata
            }
        )
        
        return response
    
    async def create_table(self, table_name: str, dimension: int, 
                          schema: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Create a new vector table"""
        
        logger.info(f"Creating table: {table_name} with dimension: {dimension}")
        
        response = await self.call_tool(
            "db_create_vector_table",
            {
                "table_name": table_name,
                "dimension": dimension,
                "additional_columns": schema or {}
            }
        )
        
        return response
    
    async def get_table_info(self, table_name: str) -> Dict[str, Any]:
        """Get information about a table"""
        
        logger.info(f"Getting info for table: {table_name}")
        
        response = await self.call_tool(
            "db_describe_table",
            {
                "table_name": table_name
            }
        )
        
        return response