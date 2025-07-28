# memory_agent.py
"""
Core Memory Agent Implementation
Handles memory operations with intelligence support
"""

from typing import Dict, List, Any, Optional
from .memory_types import Memory, MemoryType
from .intelligence import MemoryIntelligence
from ..storage.memory_storage import MemoryStorage

class MemoryAgent:
    """
    Core Memory Agent - Handles all memory operations
    Supports both basic and intelligent memory management
    """
    
    def __init__(self, storage: MemoryStorage = None, enable_intelligence: bool = True):
        """
        Initialize Memory Agent
        
        Args:
            storage: Storage backend (defaults to MemoryStorage)
            enable_intelligence: Whether to use intelligence layer for smart decisions
        """
        self.storage = storage or MemoryStorage()
        self.enable_intelligence = enable_intelligence
        self.intelligence = MemoryIntelligence() if enable_intelligence else None
    
    async def add_memory(self, user_id: str, session_id: str, content: str,
                        memory_type: MemoryType = None, importance: float = None,
                        metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Add memory with optional automatic classification
        
        Args:
            user_id: User identifier
            session_id: Session identifier 
            content: Memory content
            memory_type: Memory type (auto-classified if None and intelligence enabled)
            importance: Importance score (auto-calculated if None and intelligence enabled)
            metadata: Additional metadata
            
        Returns:
            Dict with operation status and details
        """
        try:
            # Get context for intelligent decisions
            context = {}
            if self.enable_intelligence:
                stats = await self.storage.get_memory_stats(user_id, session_id)
                context = {
                    "user_memory_count": stats.get("total_memories", 0),
                    "type_distribution": stats.get("type_distribution", {}),
                    "average_importance": stats.get("average_importance", 5.0)
                }
            
            # Auto-classify memory type if not provided
            if memory_type is None and self.intelligence:
                memory_type = self.intelligence.extract_memory_type(content, context)
            elif memory_type is None:
                memory_type = MemoryType.FACT
            
            # Auto-calculate importance if not provided
            if importance is None and self.intelligence:
                importance = self.intelligence.calculate_importance(content, memory_type, context)
            elif importance is None:
                importance = 5.0
            
            # Create and store memory
            memory = Memory(
                user_id=user_id,
                session_id=session_id,
                type=memory_type,
                content=content,
                importance=importance,
                metadata=metadata
            )
            
            success = await self.storage.store_memory(memory)
            
            result = {
                "status": "success" if success else "error",
                "memory_id": memory.id if success else None,
                "memory_type": memory_type.value,
                "importance": importance,
                "intelligence_used": self.enable_intelligence,
                "message": f"Added {memory_type.value} memory"
            }
            
            if self.enable_intelligence and success:
                # Add intelligence insights
                extracted_info = self.intelligence.extract_key_information(content)
                result["extracted_info"] = extracted_info
                result["classification_context"] = context
            
            return result
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "intelligence_used": self.enable_intelligence
            }
    
    async def process_message(self, user_id: str, session_id: str, message: str) -> Dict[str, Any]:
        """
        Process a message and decide whether to store it as memory
        Uses intelligence to make smart storage decisions
        
        Args:
            user_id: User identifier
            session_id: Session identifier
            message: Message to process
            
        Returns:
            Dict with processing results
        """
        try:
            # Get user context
            context = {}
            if self.enable_intelligence:
                stats = await self.storage.get_memory_stats(user_id, session_id)
                context = {
                    "user_memory_count": stats.get("total_memories", 0),
                    "type_distribution": stats.get("type_distribution", {}),
                    "average_importance": stats.get("average_importance", 5.0)
                }
            
            # Decide whether to store
            should_store = False
            reasoning = "No storage decision made"
            
            if self.intelligence:
                should_store = self.intelligence.should_store(message, context)
                reasoning = f"Intelligence analysis: {'store' if should_store else 'skip'}"
            else:
                # Simple fallback logic
                simple_patterns = ["저는", "개발자", "좋아해", "목표", "프로젝트"]
                should_store = any(pattern in message.lower() for pattern in simple_patterns)
                reasoning = f"Simple pattern matching: {'store' if should_store else 'skip'}"
            
            result = {
                "status": "success",
                "message": message,
                "decision": "store" if should_store else "skip",
                "reasoning": reasoning,
                "intelligence_used": self.enable_intelligence,
                "context": context
            }
            
            # Store if decision is positive
            if should_store:
                add_result = await self.add_memory(user_id, session_id, message)
                result.update({
                    "memory_added": add_result["status"] == "success",
                    "memory_details": add_result
                })
            
            return result
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "intelligence_used": self.enable_intelligence
            }
    
    async def search_memory(self, user_id: str, query: str = "", session_id: str = None,
                          memory_types: List[MemoryType] = None, limit: int = 10) -> Dict[str, Any]:
        """
        Search memories with comprehensive filtering
        
        Args:
            user_id: User identifier
            query: Search query string
            session_id: Optional session filter
            memory_types: Optional memory type filters
            limit: Maximum results to return
            
        Returns:
            Dict with search results and metadata
        """
        try:
            memories = await self.storage.search_memories(
                user_id=user_id,
                session_id=session_id,
                query=query,
                memory_types=memory_types,
                limit=limit
            )
            
            return {
                "status": "success",
                "memories": [m.to_dict() for m in memories],
                "count": len(memories),
                "search_params": {
                    "user_id": user_id,
                    "session_id": session_id,
                    "query": query,
                    "memory_types": [t.value for t in memory_types] if memory_types else None,
                    "limit": limit
                }
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "memories": [],
                "count": 0
            }
    
    async def build_context(self, user_id: str, session_id: str, 
                          current_message: str = "", enable_intelligence: bool = None) -> Dict[str, Any]:
        """
        Build conversation context from stored memories
        
        Args:
            user_id: User identifier
            session_id: Session identifier
            current_message: Current message for context
            enable_intelligence: Override intelligence setting for this call
            
        Returns:
            Dict with comprehensive context information
        """
        try:
            use_intelligence = enable_intelligence if enable_intelligence is not None else self.enable_intelligence
            
            # Get relevant memories
            memories = await self.storage.get_user_memories(user_id, session_id, limit=50)
            
            # Build basic context
            context = {
                "user_id": user_id,
                "session_id": session_id,
                "current_message": current_message,
                "total_memories": len(memories),
                "intelligence_enabled": use_intelligence
            }
            
            # Extract user profile from memories
            user_profile = {"name": None, "profession": None, "skills": [], "hobbies": [], "goals": []}
            
            for memory in memories:
                content = memory.content
                
                if memory.type == MemoryType.IDENTITY:
                    # Extract name using regex
                    import re
                    name_match = re.search(r"저는\s+([가-힣]+)", content)
                    if name_match:
                        user_profile["name"] = name_match.group(1)
                
                elif memory.type == MemoryType.PROFESSION:
                    if "개발자" in content:
                        user_profile["profession"] = "개발자"
                    elif "엔지니어" in content:
                        user_profile["profession"] = "엔지니어"
                    elif "매니저" in content:
                        user_profile["profession"] = "매니저"
                
                elif memory.type == MemoryType.SKILL:
                    user_profile["skills"].append(content)
                
                elif memory.type == MemoryType.HOBBY:
                    user_profile["hobbies"].append(content)
                
                elif memory.type == MemoryType.GOAL:
                    user_profile["goals"].append(content)
            
            context["user_profile"] = user_profile
            
            # Add intelligence-based context
            if use_intelligence and self.intelligence:
                # Get memory statistics
                stats = await self.storage.get_memory_stats(user_id, session_id)
                context["memory_stats"] = stats
                
                # Extract key information from current message
                if current_message:
                    extracted_info = self.intelligence.extract_key_information(current_message)
                    context["current_message_analysis"] = extracted_info
                
                # Get most relevant memories for current message
                if current_message:
                    relevant_memories = await self.storage.search_memories(
                        user_id, session_id, current_message, limit=5
                    )
                    context["relevant_memories"] = [m.to_dict() for m in relevant_memories]
            
            return {
                "status": "success",
                "context": context
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "context": {}
            }
    
    async def analyze_memory_health(self, user_id: str, session_id: str = None) -> Dict[str, Any]:
        """
        Analyze memory health and provide insights
        
        Args:
            user_id: User identifier
            session_id: Optional session filter
            
        Returns:
            Dict with health analysis and recommendations
        """
        try:
            stats = await self.storage.get_memory_stats(user_id, session_id)
            
            if "error" in stats:
                return {"status": "error", "error": stats["error"]}
            
            # Calculate health metrics
            total_memories = stats["total_memories"]
            avg_importance = stats["average_importance"]
            type_distribution = stats["type_distribution"]
            
            # Health scoring
            health_score = 0.0
            issues = []
            recommendations = []
            
            # Memory volume assessment
            if total_memories < 3:
                health_score += 30
                issues.append("Very few memories stored")
                recommendations.append("Engage in more conversations to build memory base")
            elif total_memories < 10:
                health_score += 60
                issues.append("Limited memory base")
                recommendations.append("Continue conversations to improve context")
            else:
                health_score += 90
            
            # Importance distribution
            if avg_importance < 4.0:
                issues.append("Low average importance - storing too much low-value information")
                recommendations.append("Focus on storing more meaningful conversations")
            elif avg_importance > 8.0:
                issues.append("Very high average importance - might be missing casual context")
                recommendations.append("Consider storing some contextual information")
            else:
                health_score += 10
            
            # Type diversity
            unique_types = len(type_distribution)
            if unique_types < 3:
                issues.append("Limited memory type diversity")
                recommendations.append("Encourage varied conversation topics")
            elif unique_types >= 5:
                health_score += 10
            
            # Final health score
            health_score = min(100, health_score)
            
            return {
                "status": "success",
                "health_score": round(health_score, 1),
                "statistics": stats,
                "issues": issues,
                "recommendations": recommendations,
                "memory_maturity": (
                    "low" if total_memories < 5 else
                    "medium" if total_memories < 20 else
                    "high"
                )
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def get_agent_info(self) -> Dict[str, Any]:
        """Get information about the memory agent configuration"""
        storage_info = self.storage.get_storage_info() if hasattr(self.storage, 'get_storage_info') else {}
        
        return {
            "agent_type": "MemoryAgent",
            "intelligence_enabled": self.enable_intelligence,
            "storage_backend": storage_info.get("backend_type", "Unknown"),
            "supports_session_id": storage_info.get("supports_session_id", False),
            "supports_search": storage_info.get("supports_search", False),
            "total_memories": storage_info.get("total_memories", 0),
            "features": {
                "auto_classification": self.enable_intelligence,
                "importance_scoring": self.enable_intelligence,
                "intelligent_storage_decisions": self.enable_intelligence,
                "context_building": True,
                "health_analysis": True,
                "multi_session_support": True
            }
        }