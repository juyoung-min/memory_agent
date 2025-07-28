"""
Vector Index Optimizer for Memory Agent
Optimizes PostgreSQL vector indexes based on data characteristics
"""

import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
import asyncio

from .clients import InternalMCPClient
from .config import get_config

logger = logging.getLogger(__name__)

class MemoryVectorIndexOptimizer:
    """Optimizes vector indexes for memory storage with user-specific considerations"""
    
    def __init__(self, db_client: InternalMCPClient):
        self.db_client = db_client
        self.config = get_config()
        self._index_stats_cache = {}
        self._last_optimization = {}
        
    async def optimize_memory_index(
        self, 
        table_name: str = "user_memories",
        force: bool = False
    ) -> Dict[str, Any]:
        """
        Optimize index for memory table considering user distribution
        
        Args:
            table_name: Table to optimize
            force: Force optimization even if recently done
            
        Returns:
            Optimization results
        """
        try:
            # Check if optimization is needed
            if not force and not await self._should_optimize(table_name):
                return {
                    "optimized": False,
                    "reason": "Recently optimized or insufficient data"
                }
            
            # Get table statistics
            stats = await self._get_table_stats(table_name)
            
            if not stats["success"]:
                return {
                    "optimized": False,
                    "error": "Failed to get table statistics"
                }
            
            # Determine optimal index strategy
            strategy = self._determine_index_strategy(stats)
            
            # Apply optimization
            result = await self._apply_index_strategy(table_name, strategy, stats)
            
            # Update optimization timestamp
            self._last_optimization[table_name] = datetime.utcnow()
            
            return result
            
        except Exception as e:
            logger.error(f"Error optimizing index: {e}")
            return {
                "optimized": False,
                "error": str(e)
            }
    
    async def _should_optimize(self, table_name: str) -> bool:
        """Check if optimization is needed"""
        # Don't optimize too frequently
        last_opt = self._last_optimization.get(table_name)
        if last_opt:
            hours_since = (datetime.utcnow() - last_opt).total_seconds() / 3600
            if hours_since < 24:  # Don't optimize more than once per day
                return False
        
        # Check if table has grown significantly
        stats = await self._get_table_stats(table_name)
        if stats.get("row_count", 0) < 100:  # Too small to optimize
            return False
            
        return True
    
    async def _get_table_stats(self, table_name: str) -> Dict[str, Any]:
        """Get detailed table statistics"""
        try:
            # Get row count and distribution
            count_result = await self.db_client.call_tool(
                "db_query",
                {
                    "query": f"""
                        SELECT 
                            COUNT(*) as total_rows,
                            COUNT(DISTINCT user_id) as unique_users,
                            COUNT(DISTINCT memory_type) as unique_types,
                            AVG(octet_length(content::text)) as avg_content_size,
                            MAX(importance) as max_importance,
                            MIN(importance) as min_importance,
                            AVG(importance) as avg_importance
                        FROM {table_name}
                    """
                }
            )
            
            if not count_result.get("success") or not count_result.get("rows"):
                return {"success": False}
            
            stats = count_result["rows"][0]
            
            # Get memory type distribution
            type_dist_result = await self.db_client.call_tool(
                "db_query",
                {
                    "query": f"""
                        SELECT 
                            memory_type,
                            COUNT(*) as count,
                            AVG(importance) as avg_importance
                        FROM {table_name}
                        GROUP BY memory_type
                        ORDER BY count DESC
                    """
                }
            )
            
            type_distribution = {}
            if type_dist_result.get("success"):
                for row in type_dist_result.get("rows", []):
                    type_distribution[row["memory_type"]] = {
                        "count": row["count"],
                        "avg_importance": row["avg_importance"]
                    }
            
            # Get user distribution
            user_dist_result = await self.db_client.call_tool(
                "db_query",
                {
                    "query": f"""
                        SELECT 
                            COUNT(*) as user_count,
                            CASE 
                                WHEN memory_count < 10 THEN 'light'
                                WHEN memory_count < 100 THEN 'medium'
                                WHEN memory_count < 1000 THEN 'heavy'
                                ELSE 'power'
                            END as user_type
                        FROM (
                            SELECT user_id, COUNT(*) as memory_count
                            FROM {table_name}
                            GROUP BY user_id
                        ) user_stats
                        GROUP BY user_type
                    """
                }
            )
            
            user_distribution = {}
            if user_dist_result.get("success"):
                for row in user_dist_result.get("rows", []):
                    user_distribution[row["user_type"]] = row["user_count"]
            
            # Check current index
            index_result = await self.db_client.call_tool(
                "db_query",
                {
                    "query": f"""
                        SELECT 
                            indexname,
                            indexdef,
                            pg_size_pretty(pg_relation_size(indexname::regclass)) as size
                        FROM pg_indexes
                        WHERE tablename = '{table_name}'
                        AND indexdef LIKE '%embedding%'
                    """
                }
            )
            
            current_indexes = []
            if index_result.get("success"):
                current_indexes = index_result.get("rows", [])
            
            return {
                "success": True,
                "row_count": int(stats["total_rows"]),
                "unique_users": int(stats["unique_users"]),
                "unique_types": int(stats["unique_types"]),
                "avg_content_size": float(stats["avg_content_size"] or 0),
                "importance_stats": {
                    "min": float(stats["min_importance"] or 0),
                    "max": float(stats["max_importance"] or 0),
                    "avg": float(stats["avg_importance"] or 0)
                },
                "type_distribution": type_distribution,
                "user_distribution": user_distribution,
                "current_indexes": current_indexes
            }
            
        except Exception as e:
            logger.error(f"Error getting table stats: {e}")
            return {"success": False, "error": str(e)}
    
    def _determine_index_strategy(self, stats: Dict[str, Any]) -> Dict[str, Any]:
        """Determine optimal index strategy based on statistics"""
        row_count = stats["row_count"]
        unique_users = stats["unique_users"]
        user_dist = stats.get("user_distribution", {})
        
        # Calculate user patterns
        power_users = user_dist.get("power", 0) + user_dist.get("heavy", 0)
        total_users = sum(user_dist.values()) if user_dist else unique_users
        power_user_ratio = power_users / total_users if total_users > 0 else 0
        
        # Determine strategy based on data characteristics
        if row_count < 1000:
            # Small dataset - no index needed
            return {
                "type": "none",
                "reason": "Dataset too small for indexing",
                "details": "Sequential scan is faster for small datasets"
            }
        
        elif row_count < 10000:
            # Small-medium dataset - basic IVFFlat
            lists = max(int(row_count / 100), 10)
            return {
                "type": "ivfflat_basic",
                "lists": lists,
                "probes": 5,
                "reason": "Small-medium dataset with basic search needs",
                "details": f"Using {lists} lists with 5 probes for balanced performance"
            }
        
        elif row_count < 100000:
            # Medium dataset - optimized IVFFlat
            if power_user_ratio > 0.2:
                # Many power users - need better accuracy
                lists = max(int(row_count / 500), 50)
                probes = 20
            else:
                # Mostly light users - can trade accuracy for speed
                lists = max(int(row_count / 1000), 30)
                probes = 10
            
            return {
                "type": "ivfflat_optimized",
                "lists": lists,
                "probes": probes,
                "reason": f"Medium dataset with {power_user_ratio:.1%} power users",
                "details": f"Using {lists} lists with {probes} probes",
                "user_optimized": power_user_ratio > 0.2
            }
        
        else:
            # Large dataset - consider HNSW or partitioned IVFFlat
            if unique_users < 1000:
                # Few users with lots of data - partition by user
                return {
                    "type": "partitioned_ivfflat",
                    "partition_by": "user_id",
                    "lists_per_partition": 100,
                    "probes": 15,
                    "reason": f"Large dataset with only {unique_users} users",
                    "details": "Partitioning by user for better locality"
                }
            else:
                # Many users - use HNSW for best accuracy
                m = 16 if row_count < 500000 else 32
                ef_construction = 200 if row_count < 500000 else 400
                
                return {
                    "type": "hnsw",
                    "m": m,
                    "ef_construction": ef_construction,
                    "ef_search": 100,
                    "reason": f"Large dataset with {unique_users} users",
                    "details": f"HNSW with m={m} for high accuracy"
                }
    
    async def _apply_index_strategy(
        self, 
        table_name: str, 
        strategy: Dict[str, Any],
        stats: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply the determined index strategy"""
        
        index_name = f"idx_{table_name}_embedding_optimized"
        
        try:
            # Drop existing index if needed
            if strategy["type"] != "none" or stats.get("current_indexes"):
                await self.db_client.call_tool(
                    "db_query",
                    {
                        "query": f"DROP INDEX IF EXISTS {index_name}"
                    }
                )
            
            if strategy["type"] == "none":
                # No index needed
                return {
                    "optimized": True,
                    "strategy": strategy,
                    "action": "Removed index for small dataset"
                }
            
            elif strategy["type"] == "ivfflat_basic":
                # Create basic IVFFlat index
                await self.db_client.call_tool(
                    "db_query",
                    {
                        "query": f"""
                            CREATE INDEX {index_name}
                            ON {table_name} 
                            USING ivfflat (embedding vector_cosine_ops)
                            WITH (lists = {strategy['lists']})
                        """
                    }
                )
                
                # Set search parameters
                await self.db_client.call_tool(
                    "db_query",
                    {
                        "query": f"SET ivfflat.probes = {strategy['probes']}"
                    }
                )
                
            elif strategy["type"] == "ivfflat_optimized":
                # Create optimized IVFFlat index
                await self.db_client.call_tool(
                    "db_query",
                    {
                        "query": f"""
                            CREATE INDEX {index_name}
                            ON {table_name} 
                            USING ivfflat (embedding vector_cosine_ops)
                            WITH (lists = {strategy['lists']})
                        """
                    }
                )
                
                # Set optimized search parameters
                await self.db_client.call_tool(
                    "db_query",
                    {
                        "query": f"SET ivfflat.probes = {strategy['probes']}"
                    }
                )
                
                # Create additional indexes for common filters
                if strategy.get("user_optimized"):
                    # Add composite index for power users
                    await self.db_client.call_tool(
                        "db_query",
                        {
                            "query": f"""
                                CREATE INDEX idx_{table_name}_user_importance
                                ON {table_name} (user_id, importance DESC)
                            """
                        }
                    )
            
            elif strategy["type"] == "hnsw":
                # Create HNSW index (if pgvector supports it)
                try:
                    await self.db_client.call_tool(
                        "db_query",
                        {
                            "query": f"""
                                CREATE INDEX {index_name}
                                ON {table_name} 
                                USING hnsw (embedding vector_cosine_ops)
                                WITH (m = {strategy['m']}, ef_construction = {strategy['ef_construction']})
                            """
                        }
                    )
                    
                    await self.db_client.call_tool(
                        "db_query",
                        {
                            "query": f"SET hnsw.ef_search = {strategy['ef_search']}"
                        }
                    )
                except Exception as e:
                    # Fallback to IVFFlat if HNSW not available
                    logger.warning(f"HNSW not available, falling back to IVFFlat: {e}")
                    strategy["type"] = "ivfflat_optimized"
                    strategy["lists"] = 1000
                    strategy["probes"] = 50
                    return await self._apply_index_strategy(table_name, strategy, stats)
            
            elif strategy["type"] == "partitioned_ivfflat":
                # For partitioned approach, we'd need table partitioning
                # For now, create optimized IVFFlat with user-based composite index
                await self.db_client.call_tool(
                    "db_query",
                    {
                        "query": f"""
                            CREATE INDEX {index_name}
                            ON {table_name} 
                            USING ivfflat (embedding vector_cosine_ops)
                            WITH (lists = {strategy['lists_per_partition'] * 10})
                        """
                    }
                )
                
                # Create composite index for user-based queries
                await self.db_client.call_tool(
                    "db_query",
                    {
                        "query": f"""
                            CREATE INDEX idx_{table_name}_user_embedding
                            ON {table_name} (user_id, embedding)
                        """
                    }
                )
            
            # Analyze table after index creation
            await self.db_client.call_tool(
                "db_query",
                {
                    "query": f"ANALYZE {table_name}"
                }
            )
            
            return {
                "optimized": True,
                "strategy": strategy,
                "action": f"Created {strategy['type']} index",
                "details": strategy.get("details", ""),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error applying index strategy: {e}")
            return {
                "optimized": False,
                "strategy": strategy,
                "error": str(e)
            }
    
    async def get_index_performance_stats(self, table_name: str = "user_memories") -> Dict[str, Any]:
        """Get index performance statistics"""
        try:
            # Get index usage stats
            usage_result = await self.db_client.call_tool(
                "db_query",
                {
                    "query": f"""
                        SELECT 
                            schemaname,
                            tablename,
                            indexname,
                            idx_scan,
                            idx_tup_read,
                            idx_tup_fetch,
                            pg_size_pretty(pg_relation_size(indexrelid)) as index_size
                        FROM pg_stat_user_indexes
                        WHERE tablename = '{table_name}'
                        AND indexname LIKE '%embedding%'
                    """
                }
            )
            
            # Get query performance
            query_stats_result = await self.db_client.call_tool(
                "db_query",
                {
                    "query": """
                        SELECT 
                            mean_exec_time,
                            stddev_exec_time,
                            calls,
                            total_exec_time
                        FROM pg_stat_statements
                        WHERE query LIKE '%user_memories%'
                        AND query LIKE '%embedding%'
                        ORDER BY mean_exec_time DESC
                        LIMIT 10
                    """
                }
            )
            
            return {
                "success": True,
                "index_usage": usage_result.get("rows", []),
                "query_performance": query_stats_result.get("rows", []),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting performance stats: {e}")
            return {"success": False, "error": str(e)}
    
    async def auto_optimize_schedule(self, interval_hours: int = 24):
        """Run optimization on a schedule"""
        while True:
            try:
                logger.info("Running scheduled index optimization")
                result = await self.optimize_memory_index()
                logger.info(f"Optimization result: {result}")
                
                await asyncio.sleep(interval_hours * 3600)
                
            except Exception as e:
                logger.error(f"Error in scheduled optimization: {e}")
                await asyncio.sleep(3600)  # Retry in 1 hour


class MemorySearchOptimizer:
    """Optimizes search queries for memory retrieval"""
    
    def __init__(self, db_client: InternalMCPClient):
        self.db_client = db_client
        self.optimizer = MemoryVectorIndexOptimizer(db_client)
        
    async def optimized_search(
        self,
        table_name: str,
        query_vector: list,
        filters: Dict[str, Any],
        limit: int = 10,
        optimize_for: str = "balanced"  # "speed", "accuracy", "balanced"
    ) -> Dict[str, Any]:
        """
        Perform optimized vector search
        
        Args:
            table_name: Table to search
            query_vector: Query embedding vector
            filters: Search filters
            limit: Number of results
            optimize_for: Optimization target
            
        Returns:
            Search results with performance metrics
        """
        start_time = datetime.utcnow()
        
        try:
            # Get current index stats
            stats = await self.optimizer._get_table_stats(table_name)
            
            # Adjust search parameters based on optimization target
            search_params = self._get_search_params(stats, optimize_for)
            
            # Set search parameters
            if search_params.get("probes"):
                await self.db_client.call_tool(
                    "db_query",
                    {"query": f"SET LOCAL ivfflat.probes = {search_params['probes']}"}
                )
            
            # Build optimized query
            query = self._build_optimized_query(
                table_name, 
                query_vector, 
                filters, 
                limit,
                search_params
            )
            
            # Execute search
            result = await self.db_client.call_tool("db_query", {"query": query})
            
            # Calculate performance metrics
            end_time = datetime.utcnow()
            duration_ms = (end_time - start_time).total_seconds() * 1000
            
            return {
                "success": result.get("success", False),
                "results": result.get("rows", []),
                "performance": {
                    "duration_ms": duration_ms,
                    "optimization": optimize_for,
                    "parameters": search_params
                }
            }
            
        except Exception as e:
            logger.error(f"Error in optimized search: {e}")
            return {"success": False, "error": str(e)}
    
    def _get_search_params(
        self, 
        stats: Dict[str, Any], 
        optimize_for: str
    ) -> Dict[str, Any]:
        """Get search parameters based on optimization target"""
        row_count = stats.get("row_count", 0)
        
        if optimize_for == "speed":
            # Optimize for speed - less probes, may sacrifice accuracy
            if row_count < 10000:
                return {"probes": 1}
            elif row_count < 100000:
                return {"probes": 5}
            else:
                return {"probes": 10}
                
        elif optimize_for == "accuracy":
            # Optimize for accuracy - more probes
            if row_count < 10000:
                return {"probes": 10}
            elif row_count < 100000:
                return {"probes": 50}
            else:
                return {"probes": 100}
                
        else:  # balanced
            # Balanced approach
            if row_count < 10000:
                return {"probes": 5}
            elif row_count < 100000:
                return {"probes": 20}
            else:
                return {"probes": 40}
    
    def _build_optimized_query(
        self,
        table_name: str,
        query_vector: list,
        filters: Dict[str, Any],
        limit: int,
        search_params: Dict[str, Any]
    ) -> str:
        """Build optimized search query"""
        # Convert vector to string format
        vector_str = '[' + ','.join(map(str, query_vector)) + ']'
        
        # Build WHERE clause
        where_clauses = []
        if filters:
            for key, value in filters.items():
                if isinstance(value, dict) and "$in" in value:
                    values = "','".join(value["$in"])
                    where_clauses.append(f"{key} IN ('{values}')")
                elif isinstance(value, dict) and "$gte" in value:
                    where_clauses.append(f"{key} >= {value['$gte']}")
                else:
                    where_clauses.append(f"{key} = '{value}'")
        
        where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"
        
        # Build query with optimization hints
        query = f"""
            SELECT 
                id,
                content,
                user_id,
                session_id,
                memory_type,
                importance,
                timestamp,
                1 - (embedding <=> '{vector_str}'::vector) as similarity
            FROM {table_name}
            WHERE {where_clause}
            ORDER BY embedding <=> '{vector_str}'::vector
            LIMIT {limit}
        """
        
        return query