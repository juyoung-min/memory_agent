"""
Vector Index Optimization Tools
Provides MCP tools for managing and optimizing vector indexes
"""

import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime

from mcp_instance import mcp
from src.clients import InternalMCPClient
from src.vector_index_optimizer import MemoryVectorIndexOptimizer
from src.config import get_config

# Initialize
config = get_config()
logger = logging.getLogger(__name__)

# Initialize clients
db_client = InternalMCPClient("http://mcp-db:8092/sse", timeout=30)

# Initialize optimizer
index_optimizer = MemoryVectorIndexOptimizer(db_client)

@mcp.tool(description="Optimize vector index for memory storage")
async def optimize_vector_index(
    table_name: str = "user_memories",
    force: bool = False
) -> str:
    """
    Optimize vector index based on current data characteristics
    
    Args:
        table_name: Table to optimize (default: user_memories)
        force: Force optimization even if recently done
        
    Returns:
        Optimization results
    """
    try:
        logger.info(f"Starting index optimization for {table_name}")
        
        # Run optimization
        result = await index_optimizer.optimize_memory_index(
            table_name=table_name,
            force=force
        )
        
        return json.dumps({
            "success": result.get("optimized", False),
            "table": table_name,
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error optimizing index: {e}", exc_info=True)
        return json.dumps({
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        })

@mcp.tool(description="Get vector index performance statistics")
async def get_index_performance_stats(
    table_name: str = "user_memories"
) -> str:
    """
    Get performance statistics for vector indexes
    
    Args:
        table_name: Table to analyze
        
    Returns:
        Performance statistics
    """
    try:
        stats = await index_optimizer.get_index_performance_stats(table_name)
        
        return json.dumps({
            "success": stats.get("success", False),
            "table": table_name,
            "stats": stats,
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting performance stats: {e}")
        return json.dumps({
            "success": False,
            "error": str(e)
        })

@mcp.tool(description="Get detailed table statistics for optimization")
async def get_memory_table_stats(
    table_name: str = "user_memories"
) -> str:
    """
    Get detailed statistics about memory table for optimization insights
    
    Args:
        table_name: Table to analyze
        
    Returns:
        Detailed table statistics
    """
    try:
        stats = await index_optimizer._get_table_stats(table_name)
        
        if not stats.get("success"):
            return json.dumps({
                "success": False,
                "error": "Failed to get table statistics"
            })
        
        # Determine recommended strategy
        strategy = index_optimizer._determine_index_strategy(stats)
        
        return json.dumps({
            "success": True,
            "table": table_name,
            "statistics": {
                "row_count": stats["row_count"],
                "unique_users": stats["unique_users"],
                "unique_memory_types": stats["unique_types"],
                "avg_content_size": stats["avg_content_size"],
                "importance_range": {
                    "min": stats["importance_stats"]["min"],
                    "max": stats["importance_stats"]["max"],
                    "avg": stats["importance_stats"]["avg"]
                },
                "type_distribution": stats["type_distribution"],
                "user_distribution": stats["user_distribution"],
                "current_indexes": stats["current_indexes"]
            },
            "recommended_strategy": strategy,
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting table stats: {e}")
        return json.dumps({
            "success": False,
            "error": str(e)
        })

@mcp.tool(description="Manually set vector search parameters")
async def set_vector_search_params(
    probes: Optional[int] = None,
    ef_search: Optional[int] = None
) -> str:
    """
    Manually set vector search parameters for tuning
    
    Args:
        probes: IVFFlat probes parameter (1-1000)
        ef_search: HNSW ef_search parameter (10-500)
        
    Returns:
        Parameter update results
    """
    try:
        results = []
        
        if probes is not None:
            if not 1 <= probes <= 1000:
                return json.dumps({
                    "success": False,
                    "error": "probes must be between 1 and 1000"
                })
            
            probe_result = await db_client.call_tool(
                "db_query",
                {"query": f"SET ivfflat.probes = {probes}"}
            )
            
            results.append({
                "parameter": "ivfflat.probes",
                "value": probes,
                "success": probe_result.get("success", False)
            })
        
        if ef_search is not None:
            if not 10 <= ef_search <= 500:
                return json.dumps({
                    "success": False,
                    "error": "ef_search must be between 10 and 500"
                })
            
            ef_result = await db_client.call_tool(
                "db_query",
                {"query": f"SET hnsw.ef_search = {ef_search}"}
            )
            
            results.append({
                "parameter": "hnsw.ef_search",
                "value": ef_search,
                "success": ef_result.get("success", False)
            })
        
        return json.dumps({
            "success": all(r["success"] for r in results),
            "parameters_set": results,
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error setting search params: {e}")
        return json.dumps({
            "success": False,
            "error": str(e)
        })

@mcp.tool(description="Benchmark vector search performance")
async def benchmark_vector_search(
    table_name: str = "user_memories",
    sample_size: int = 10,
    test_queries: Optional[int] = None
) -> str:
    """
    Benchmark vector search performance with different optimization settings
    
    Args:
        table_name: Table to benchmark
        sample_size: Number of results per query
        test_queries: Number of test queries (default: 5)
        
    Returns:
        Benchmark results
    """
    try:
        if test_queries is None:
            test_queries = 5
        
        # Get sample memories for test queries
        sample_result = await db_client.call_tool(
            "db_query",
            {
                "query": f"""
                    SELECT content, embedding
                    FROM {table_name}
                    ORDER BY RANDOM()
                    LIMIT {test_queries}
                """
            }
        )
        
        if not sample_result.get("success") or not sample_result.get("rows"):
            return json.dumps({
                "success": False,
                "error": "No data available for benchmarking"
            })
        
        # Initialize search optimizer
        from src.vector_index_optimizer import MemorySearchOptimizer
        search_optimizer = MemorySearchOptimizer(db_client)
        
        benchmarks = []
        
        # Test different optimization settings
        for optimization in ["speed", "balanced", "accuracy"]:
            optimization_results = []
            
            for row in sample_result["rows"]:
                if row.get("embedding"):
                    # Parse embedding
                    embedding = row["embedding"]
                    if isinstance(embedding, str):
                        # Parse vector string format
                        embedding = json.loads(embedding.replace('[', '').replace(']', '').split(','))
                    
                    # Run search
                    start_time = datetime.utcnow()
                    
                    search_result = await search_optimizer.optimized_search(
                        table_name=table_name,
                        query_vector=embedding,
                        filters={},
                        limit=sample_size,
                        optimize_for=optimization
                    )
                    
                    if search_result.get("success"):
                        duration = search_result["performance"]["duration_ms"]
                        result_count = len(search_result["results"])
                        
                        optimization_results.append({
                            "duration_ms": duration,
                            "result_count": result_count
                        })
            
            if optimization_results:
                avg_duration = sum(r["duration_ms"] for r in optimization_results) / len(optimization_results)
                
                benchmarks.append({
                    "optimization": optimization,
                    "avg_duration_ms": round(avg_duration, 2),
                    "queries_tested": len(optimization_results),
                    "avg_results": sum(r["result_count"] for r in optimization_results) / len(optimization_results)
                })
        
        return json.dumps({
            "success": True,
            "table": table_name,
            "benchmarks": benchmarks,
            "test_configuration": {
                "sample_size": sample_size,
                "test_queries": test_queries
            },
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error benchmarking: {e}", exc_info=True)
        return json.dumps({
            "success": False,
            "error": str(e)
        })

# Initialize on module load
logger.info("Vector Index Optimization tools loaded")