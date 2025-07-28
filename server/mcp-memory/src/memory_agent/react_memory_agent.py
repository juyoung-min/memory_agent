"""
ReactMemoryAgent - Memory Agent with Tool Orchestration
Implements ReAct pattern with intelligence as queryable tools
"""

from typing import Dict, List, Any, Optional
from .memory_types import Memory, MemoryType
from .intelligence import MemoryIntelligence
from ..storage.memory_storage import MemoryStorage
from .tools import MemoryIntelligenceTools
import asyncio

class ReactMemoryAgent:
    """
    React Memory Agent that orchestrates intelligence tools
    Uses ReAct pattern: Reason → Act (Tool) → Observe → Repeat
    """
    
    def __init__(self, storage: MemoryStorage = None, enable_intelligence: bool = True, config: Dict[str, Any] = None):
        """
        Initialize ReactMemoryAgent
        
        Args:
            storage: Storage backend
            enable_intelligence: Whether to use intelligence tools
            config: Agent configuration
        """
        self.storage = storage or MemoryStorage()
        self.enable_intelligence = enable_intelligence
        self.config = config or self._default_config()
        
        # Initialize intelligence tools
        self.tools = MemoryIntelligenceTools(self.storage) if enable_intelligence else None
        
        # Reasoning state
        self.reasoning_steps = []
        self.tool_results = []
        
    def _default_config(self) -> Dict[str, Any]:
        """Default configuration for ReactMemoryAgent"""
        return {
            "max_reasoning_steps": 8,
            "enable_detailed_logging": True,
            "importance_threshold": 6.0,
            "context_window_size": 10,
            "tool_orchestration_strategy": "comprehensive"  # or "minimal"
        }
    
    async def process_message(self, user_id: str, session_id: str, message: str, 
                            context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Process message using React-style reasoning and tool orchestration
        
        Args:
            user_id: User identifier
            session_id: Session identifier
            message: User message to process
            context: Additional context
            
        Returns:
            Dict with processing results and reasoning trace
        """
        if not self.enable_intelligence:
            return await self._simple_fallback(user_id, session_id, message)
        
        # Reset reasoning state
        self.reasoning_steps = []
        self.tool_results = []
        
        if self.config.get("enable_detailed_logging", True):
            print(f"🤖 ReactMemoryAgent: Processing message for {user_id}")
        
        # Start React reasoning loop
        return await self._react_reasoning_loop(user_id, session_id, message, context)
    
    async def _react_reasoning_loop(self, user_id: str, session_id: str, 
                                  message: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Main React reasoning loop with tool orchestration
        """
        context = context or {}
        
        # STEP 1: Analyze message importance
        await self._think("I need to analyze if this message is worth storing")
        importance_result = await self._use_tool(
            "analyze_message_importance", 
            {"message": message, "user_context": context}
        )
        
        if importance_result.get("recommendation") == "skip":
            return {
                "status": "success",
                "decision": "skip",
                "reasoning": f"Low importance score: {importance_result.get('importance_score')}/10",
                "reasoning_steps": self.reasoning_steps,
                "tool_results": self.tool_results
            }
        
        # STEP 2: Search for related memories to understand context
        await self._think("Let me search for related memories to understand user context")
        search_result = await self._use_tool(
            "search_related_memories",
            {"user_id": user_id, "query": message, "session_id": session_id}
        )
        
        # STEP 3: Analyze user patterns for adaptive behavior
        await self._think("I should analyze user patterns to adapt my behavior")
        patterns_result = await self._use_tool(
            "analyze_user_patterns",
            {"user_id": user_id, "session_id": session_id}
        )
        
        # STEP 4: Classify memory type with context awareness
        await self._think("Now I'll classify the memory type considering the context")
        classification_result = await self._use_tool(
            "classify_memory_type",
            {"message": message, "context_memories": search_result.get("memories", [])}
        )
        
        # STEP 5: Calculate contextual importance
        await self._think("Finally, I'll adjust importance based on user context")
        contextual_importance = await self._use_tool(
            "calculate_contextual_importance",
            {
                "base_importance": importance_result.get("importance_score"),
                "user_patterns": patterns_result,
                "message_type": classification_result.get("memory_type")
            }
        )
        
        # STEP 6: Make final decision and store
        final_importance = contextual_importance.get("adjusted_importance")
        memory_type = MemoryType(classification_result.get("memory_type"))
        
        # Create and store memory
        memory = Memory(
            user_id=user_id,
            session_id=session_id,
            type=memory_type,
            content=message,
            importance=final_importance,
            metadata={
                "react_agent_analysis": {
                    "tool_results": self.tool_results,
                    "reasoning_steps": self.reasoning_steps,
                    "agent_version": "ReactMemoryAgent_v1.0"
                }
            }
        )
        
        success = await self.storage.store_memory(memory)
        
        if success:
            await self._think(f"Successfully stored memory with importance {final_importance}/10")
        else:
            await self._think("Failed to store memory - storage error")
        
        return {
            "status": "success" if success else "error",
            "decision": "stored" if success else "storage_failed",
            "memory_id": memory.id if success else None,
            "memory_type": memory_type.value,
            "final_importance": final_importance,
            "reasoning_steps": self.reasoning_steps,
            "tool_results": self.tool_results,
            "agent_reasoning": f"Orchestrated {len(self.tool_results)} tools for informed decision"
        }
    
    async def _think(self, thought: str):
        """Record a reasoning step"""
        self.reasoning_steps.append(f"💭 {thought}")
        if self.config.get("enable_detailed_logging", True):
            print(f"   💭 Agent: {thought}")
    
    async def _use_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool and record the result"""
        if not self.tools:
            return {"error": "Intelligence tools not available"}
        
        try:
            # Get tool method
            tool_method = getattr(self.tools, f"{tool_name}_tool", None)
            if not tool_method:
                return {"error": f"Tool {tool_name} not found"}
            
            # Execute tool
            result = await tool_method(**tool_input)
            result["tool_name"] = tool_name
            
            # Record tool usage
            self.tool_results.append(result)
            self.reasoning_steps.append(f"🔧 Used {tool_name}: {result.get('reasoning', 'completed')}")
            
            if self.config.get("enable_detailed_logging", True):
                print(f"   🔧 Tool {tool_name}: {result.get('reasoning', 'completed')}")
            
            return result
            
        except Exception as e:
            error_result = {"error": str(e), "tool_name": tool_name}
            self.tool_results.append(error_result)
            return error_result
    
    async def _simple_fallback(self, user_id: str, session_id: str, message: str) -> Dict[str, Any]:
        """Fallback when intelligence is disabled"""
        # Simple pattern matching
        if any(word in message.lower() for word in ["저는", "개발자", "좋아해", "목표"]):
            memory = Memory(user_id, session_id, MemoryType.FACT, message, 5.0)
            success = await self.storage.store_memory(memory)
            return {
                "status": "success",
                "decision": "stored" if success else "storage_failed",
                "memory_type": "fact",
                "intelligence_enabled": False,
                "reasoning": "Simple pattern matching fallback"
            }
        
        return {
            "status": "success",
            "decision": "skip",
            "intelligence_enabled": False,
            "reasoning": "No patterns matched in fallback mode"
        }
    
    async def search_memory(self, user_id: str, query: str = "", session_id: str = None,
                          memory_types: List[MemoryType] = None, limit: int = 10) -> Dict[str, Any]:
        """
        Search memories with React-style analysis
        """
        try:
            memories = await self.storage.search_memories(
                user_id, session_id, query, memory_types, limit
            )
            
            # Convert Memory objects to dictionaries for JSON serialization
            memory_dicts = []
            for memory in memories:
                memory_dict = {
                    "id": memory.id,
                    "user_id": memory.user_id,
                    "session_id": memory.session_id,
                    "type": memory.type.value,
                    "content": memory.content,
                    "importance": memory.importance,
                    "timestamp": memory.timestamp.isoformat(),
                    "metadata": memory.metadata
                }
                memory_dicts.append(memory_dict)
            
            return {
                "status": "success",
                "memories": memory_dicts,
                "total_found": len(memories),
                "search_query": query,
                "search_filters": {
                    "session_id": session_id,
                    "memory_types": [mt.value for mt in memory_types] if memory_types else None,
                    "limit": limit
                }
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "memories": []
            }
    
    async def build_context(self, user_id: str, session_id: str, current_message: str = "") -> Dict[str, Any]:
        """
        Build comprehensive context using React-style analysis
        """
        try:
            # Get user memories
            memories = await self.storage.get_user_memories(user_id, session_id, limit=50)
            
            # Analyze memories to build profile
            profile = {
                "name": None,
                "profession": None,
                "skills": [],
                "hobbies": [],
                "goals": [],
                "preferences": []
            }
            
            recent_conversations = []
            
            for memory in memories[-10:]:  # Last 10 memories
                content = memory.content.lower()
                
                # Extract profile information
                if memory.type == MemoryType.IDENTITY and "저는" in content:
                    # Extract name
                    import re
                    name_match = re.search(r"저는\s+([가-힣]+)", content)
                    if name_match and not profile["name"]:
                        profile["name"] = name_match.group(1)
                
                if memory.type == MemoryType.PROFESSION:
                    if "개발자" in content and "개발자" not in profile["profession"] if profile["profession"] else True:
                        profile["profession"] = "개발자"
                
                # Extract skills
                tech_terms = ["파이썬", "자바", "자바스크립트", "리액트"]
                for tech in tech_terms:
                    if tech in content and tech not in profile["skills"]:
                        profile["skills"].append(f"{tech} 기술")
                
                # Extract hobbies
                hobby_terms = ["등산", "독서", "여행", "음악"]
                for hobby in hobby_terms:
                    if hobby in content and hobby not in profile["hobbies"]:
                        profile["hobbies"].append(f"{hobby} 취미")
                
                # Recent conversations
                if memory.type in [MemoryType.CONVERSATION, MemoryType.CONTEXT]:
                    recent_conversations.append({
                        "content": memory.content[:100],
                        "timestamp": memory.timestamp.isoformat(),
                        "importance": memory.importance
                    })
            
            return {
                "status": "success",
                "context": {
                    "user_profile": profile,
                    "recent_conversations": recent_conversations,
                    "total_memories": len(memories),
                    "session_info": {
                        "user_id": user_id,
                        "session_id": session_id,
                        "current_message": current_message
                    }
                }
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "context": {}
            }
    
    async def analyze_memory_health(self, user_id: str, session_id: str = None) -> Dict[str, Any]:
        """
        Analyze memory health and provide recommendations
        """
        try:
            stats = await self.storage.get_memory_stats(user_id, session_id)
            
            total_memories = stats.get("total_memories", 0)
            avg_importance = stats.get("average_importance", 0)
            type_distribution = stats.get("type_distribution", {})
            
            # Calculate health score
            health_score = 0
            recommendations = []
            
            # Memory quantity health
            if total_memories >= 20:
                health_score += 30
            elif total_memories >= 10:
                health_score += 20
                recommendations.append("Continue building memory base")
            else:
                health_score += 10
                recommendations.append("Need more conversations to build comprehensive memory")
            
            # Memory quality health (importance)
            if avg_importance >= 7.0:
                health_score += 30
            elif avg_importance >= 5.0:
                health_score += 20
                recommendations.append("Focus on storing higher quality information")
            else:
                health_score += 10
                recommendations.append("Improve memory importance by storing more significant information")
            
            # Memory diversity health
            unique_types = len(type_distribution)
            if unique_types >= 5:
                health_score += 40
            elif unique_types >= 3:
                health_score += 25
                recommendations.append("Expand memory type diversity")
            else:
                health_score += 10
                recommendations.append("Store more diverse types of information")
            
            # Determine maturity level
            if total_memories >= 30:
                maturity = "high"
            elif total_memories >= 10:
                maturity = "medium"
            else:
                maturity = "low"
            
            return {
                "status": "success",
                "health_score": min(100, health_score),
                "memory_maturity": maturity,
                "total_memories": total_memories,
                "average_importance": avg_importance,
                "type_diversity": unique_types,
                "recommendations": recommendations
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "health_score": 0
            }