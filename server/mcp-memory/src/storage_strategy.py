"""
Storage Strategy Module
Determines optimal storage approach for different memory types
"""

from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from enum import Enum

class StorageLocation(Enum):
    """Available storage locations"""
    DB = "database"          # PostgreSQL with pgvector
    RAG = "rag_index"       # RAG-MCP for retrieval
    CACHE = "cache"         # Redis/in-memory cache
    ARCHIVE = "archive"     # Long-term cold storage

@dataclass
class StorageStrategy:
    """Storage strategy configuration"""
    primary_location: StorageLocation
    secondary_locations: List[StorageLocation]
    includes_rag: bool
    includes_embedding: bool
    ttl_seconds: Optional[int]  # Time to live
    compression_enabled: bool
    index_for_search: bool
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "primary": self.primary_location.value,
            "secondary": [loc.value for loc in self.secondary_locations],
            "rag_enabled": self.includes_rag,
            "embedding_enabled": self.includes_embedding,
            "ttl": self.ttl_seconds,
            "compression": self.compression_enabled,
            "searchable": self.index_for_search
        }

class StorageStrategyDeterminer:
    """Determines optimal storage strategy based on memory characteristics"""
    
    def __init__(self):
        # Define strategies for different scenarios
        self.strategies = {
            # High-value, frequently accessed
            "high_value_frequent": StorageStrategy(
                primary_location=StorageLocation.DB,
                secondary_locations=[StorageLocation.RAG, StorageLocation.CACHE],
                includes_rag=True,
                includes_embedding=True,
                ttl_seconds=None,  # No expiration
                compression_enabled=False,
                index_for_search=True
            ),
            
            # High-value, infrequent access
            "high_value_infrequent": StorageStrategy(
                primary_location=StorageLocation.DB,
                secondary_locations=[StorageLocation.ARCHIVE],
                includes_rag=False,
                includes_embedding=True,
                ttl_seconds=None,
                compression_enabled=True,
                index_for_search=True
            ),
            
            # Conversational (store in DB)
            "conversational": StorageStrategy(
                primary_location=StorageLocation.DB,
                secondary_locations=[],
                includes_rag=False,
                includes_embedding=True,
                ttl_seconds=None,
                compression_enabled=False,
                index_for_search=True
            ),
            
            # Temporary context
            "temporary": StorageStrategy(
                primary_location=StorageLocation.CACHE,
                secondary_locations=[],
                includes_rag=False,
                includes_embedding=False,
                ttl_seconds=86400,  # 24 hours
                compression_enabled=False,
                index_for_search=False
            ),
            
            # Large content (experiences, documents)
            "large_content": StorageStrategy(
                primary_location=StorageLocation.DB,
                secondary_locations=[StorageLocation.ARCHIVE],
                includes_rag=False,
                includes_embedding=True,
                ttl_seconds=None,
                compression_enabled=True,
                index_for_search=True
            )
        }
    
    def determine_strategy(
        self,
        memory_type: str,
        importance: float,
        content_size: int,
        access_pattern: Optional[str] = None
    ) -> StorageStrategy:
        """Determine optimal storage strategy"""
        
        # Hierarchical memory type handling
        if "/" in memory_type:
            major, minor, detail = memory_type.split("/")
            return self._determine_hierarchical_strategy(
                major, minor, detail, importance, content_size
            )
        
        # Legacy flat memory types
        return self._determine_flat_strategy(
            memory_type, importance, content_size, access_pattern
        )
    
    def _determine_hierarchical_strategy(
        self,
        major: str,
        minor: str,
        detail: str,
        importance: float,
        content_size: int
    ) -> StorageStrategy:
        """Determine strategy for hierarchical memory types"""
        
        # Personal memories - high value, need protection
        if major == "personal":
            if minor == "identity":
                return self.strategies["high_value_frequent"]
            elif minor == "preference":
                if importance >= 7:
                    return self.strategies["high_value_frequent"]
                else:
                    return self.strategies["high_value_infrequent"]
            elif minor == "profession":
                return self.strategies["high_value_frequent"]
        
        # Knowledge - depends on type
        elif major == "knowledge":
            if minor == "skill":
                return self.strategies["high_value_frequent"]
            elif minor == "experience":
                if content_size > 1000:  # Long experiences
                    return self.strategies["large_content"]
                else:
                    return self.strategies["conversational"]
            elif minor == "fact":
                if importance >= 8:
                    return self.strategies["high_value_infrequent"]
                else:
                    return StorageStrategy(
                        primary_location=StorageLocation.DB,
                        secondary_locations=[],
                        includes_rag=False,
                        includes_embedding=True,
                        ttl_seconds=None,
                        compression_enabled=False,
                        index_for_search=True
                    )
        
        # Temporal - mostly conversational
        elif major == "temporal":
            if minor == "conversation":
                return self.strategies["conversational"]
            elif minor == "context":
                return self.strategies["temporary"]
        
        # Default strategy
        return self._get_default_strategy(importance, content_size)
    
    def _determine_flat_strategy(
        self,
        memory_type: str,
        importance: float,
        content_size: int,
        access_pattern: Optional[str]
    ) -> StorageStrategy:
        """Determine strategy for flat memory types"""
        
        if memory_type == "conversation":
            return self.strategies["conversational"]
        elif memory_type == "identity":
            return self.strategies["high_value_frequent"]
        elif memory_type == "preference":
            return self.strategies["high_value_frequent"]
        elif memory_type == "experience":
            if content_size > 1000:
                return self.strategies["large_content"]
            return self.strategies["conversational"]
        elif memory_type == "context":
            return self.strategies["temporary"]
        else:
            return self._get_default_strategy(importance, content_size)
    
    def _get_default_strategy(
        self, 
        importance: float, 
        content_size: int
    ) -> StorageStrategy:
        """Get default strategy based on importance and size"""
        
        if importance >= 8:
            return self.strategies["high_value_frequent"]
        elif importance >= 6:
            if content_size > 1000:
                return self.strategies["large_content"]
            return self.strategies["high_value_infrequent"]
        elif importance >= 4:
            return self.strategies["conversational"]
        else:
            return self.strategies["temporary"]
    
    def get_storage_cost(self, strategy: StorageStrategy, content_size: int) -> Dict[str, float]:
        """Estimate storage cost for strategy"""
        
        # Cost factors (relative units)
        location_costs = {
            StorageLocation.DB: 1.0,
            StorageLocation.RAG: 2.0,      # More expensive due to indexing
            StorageLocation.CACHE: 3.0,     # RAM is expensive
            StorageLocation.ARCHIVE: 0.3    # Cheap cold storage
        }
        
        # Calculate base cost
        base_cost = location_costs[strategy.primary_location]
        
        # Add secondary storage costs
        for loc in strategy.secondary_locations:
            base_cost += location_costs[loc] * 0.5  # Secondary is cheaper
        
        # Factor in features
        if strategy.includes_embedding:
            base_cost += 0.5  # Embedding generation cost
        if strategy.includes_rag:
            base_cost += 1.0  # RAG indexing cost
        if strategy.compression_enabled:
            base_cost *= 0.7  # Compression saves space
        
        # Factor in content size (KB)
        size_factor = content_size / 1024
        total_cost = base_cost * (1 + size_factor * 0.1)
        
        return {
            "storage_cost": round(total_cost, 2),
            "retrieval_cost": round(total_cost * 0.1, 2),  # 10% of storage
            "total_monthly": round(total_cost * 1.1 * 30, 2)  # 30 days
        }
    
    def optimize_strategy(
        self,
        current_strategy: StorageStrategy,
        access_stats: Dict[str, Any]
    ) -> StorageStrategy:
        """Optimize strategy based on actual usage patterns"""
        
        access_frequency = access_stats.get("daily_access_count", 0)
        last_accessed_days = access_stats.get("days_since_last_access", 0)
        search_hit_rate = access_stats.get("search_hit_rate", 0.0)
        
        # Clone current strategy
        optimized = StorageStrategy(
            primary_location=current_strategy.primary_location,
            secondary_locations=current_strategy.secondary_locations.copy(),
            includes_rag=current_strategy.includes_rag,
            includes_embedding=current_strategy.includes_embedding,
            ttl_seconds=current_strategy.ttl_seconds,
            compression_enabled=current_strategy.compression_enabled,
            index_for_search=current_strategy.index_for_search
        )
        
        # Optimize based on access patterns
        if access_frequency > 10:  # Frequently accessed
            # Add to cache if not already there
            if StorageLocation.CACHE not in optimized.secondary_locations:
                optimized.secondary_locations.append(StorageLocation.CACHE)
        
        elif last_accessed_days > 30:  # Not accessed for a month
            # Move to archive
            if StorageLocation.ARCHIVE not in optimized.secondary_locations:
                optimized.secondary_locations.append(StorageLocation.ARCHIVE)
            # Remove from cache
            if StorageLocation.CACHE in optimized.secondary_locations:
                optimized.secondary_locations.remove(StorageLocation.CACHE)
            # Enable compression
            optimized.compression_enabled = True
        
        # Optimize search indexing
        if search_hit_rate < 0.1 and optimized.includes_rag:
            # Low search hits, consider removing from RAG
            optimized.includes_rag = False
            if StorageLocation.RAG in optimized.secondary_locations:
                optimized.secondary_locations.remove(StorageLocation.RAG)
        
        return optimized