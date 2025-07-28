"""
Memory Intelligence Tools - Intelligence as queryable tools for ReactMemoryAgent
Converts intelligence capabilities into discrete tools that agents can orchestrate
"""

from typing import Dict, List, Any, Optional
from .memory_types import Memory, MemoryType
from .intelligence import MemoryIntelligence
from ..storage.memory_storage import MemoryStorage

class MemoryIntelligenceTools:
    """
    Intelligence layer converted to tools that React agents can use and orchestrate
    Each method is a discrete tool that provides specific intelligence capabilities
    """
    
    def __init__(self, storage: MemoryStorage):
        self.storage = storage
        self.intelligence = MemoryIntelligence()
    
    async def analyze_message_importance_tool(self, message: str, user_context: Dict = None) -> Dict[str, Any]:
        """
        TOOL: Analyze message importance with detailed reasoning
        React agent can call this to understand if something should be stored
        """
        importance_indicators = []
        base_score = 3.0
        
        message_lower = message.lower()
        
        # Identity indicators (high value)
        if any(pattern in message_lower for pattern in ["저는", "제가", "이름"]):
            importance_indicators.append("Contains identity information")
            base_score += 4.0
        
        # Professional indicators
        if any(pattern in message_lower for pattern in ["개발자", "엔지니어", "회사", "업무"]):
            importance_indicators.append("Contains professional information")
            base_score += 3.5
        
        # Technical skills
        if any(pattern in message_lower for pattern in ["파이썬", "자바", "프로그래밍", "기술"]):
            importance_indicators.append("Contains technical skills")
            base_score += 3.0
        
        # Goals and plans
        if any(pattern in message_lower for pattern in ["목표", "계획", "하고싶", "원해"]):
            importance_indicators.append("Contains goals/aspirations")
            base_score += 3.0
        
        # Personal interests
        if any(pattern in message_lower for pattern in ["좋아해", "취미", "관심"]):
            importance_indicators.append("Contains personal interests")
            base_score += 2.5
        
        # Temporal relevance
        if any(pattern in message_lower for pattern in ["현재", "지금", "최근", "오늘"]):
            importance_indicators.append("Contains current/recent information")
            base_score += 1.0
        
        final_score = min(10.0, base_score)
        recommendation = "store" if final_score >= 6.0 else "skip"
        
        return {
            "tool_name": "analyze_message_importance",
            "importance_score": final_score,
            "indicators": importance_indicators,
            "recommendation": recommendation,
            "reasoning": f"Found {len(importance_indicators)} importance indicators",
            "details": {
                "message_length": len(message.split()),
                "complexity": "high" if len(importance_indicators) > 2 else "medium" if len(importance_indicators) > 0 else "low"
            }
        }
    
    async def search_related_memories_tool(self, user_id: str, query: str, session_id: str = None) -> Dict[str, Any]:
        """
        TOOL: Search for memories related to current context
        React agent can use this to understand user history before making decisions
        """
        memories = await self.storage.search_memories(user_id, session_id, query, limit=5)
        
        memory_summaries = []
        for memory in memories:
            memory_summaries.append({
                "content": memory.content,
                "type": memory.type.value,
                "importance": memory.importance,
                "timestamp": memory.timestamp.isoformat(),
                "relevance": self._calculate_relevance(query, memory.content)
            })
        
        return {
            "tool_name": "search_related_memories",
            "memories_found": len(memories),
            "memories": memory_summaries,
            "search_summary": f"Found {len(memories)} related memories for query: '{query}'",
            "relevance_indicators": [
                f"Memory {i+1}: {m['type']}" for i, m in enumerate(memory_summaries[:3])
            ]
        }
    
    async def classify_memory_type_tool(self, message: str, context_memories: List[Dict] = None) -> Dict[str, Any]:
        """
        TOOL: Intelligently classify memory type considering context
        React agent can use this after searching to make informed classification
        """
        content = message.lower()
        type_scores = {}
        
        # Identity classification
        if any(word in content for word in ["저는", "제가", "이름"]):
            type_scores["identity"] = 0.9
        
        # Professional classification  
        if any(word in content for word in ["개발자", "엔지니어", "회사", "직업"]):
            type_scores["profession"] = 0.85
        
        # Technical skills
        if any(word in content for word in ["파이썬", "자바", "프로그래밍", "기술"]):
            type_scores["skill"] = 0.8
        
        # Goals
        if any(word in content for word in ["목표", "계획", "하고싶"]):
            type_scores["goal"] = 0.8
        
        # Experience
        if any(word in content for word in ["프로젝트", "경험", "작업", "개발한"]):
            type_scores["experience"] = 0.75
        
        # Hobbies (specific activities)
        hobby_indicators = ["등산", "독서", "여행", "음악", "운동", "게임"]
        hobby_patterns = ["취미", "즐겨", "좋아해"]
        if (any(pattern in content for pattern in hobby_patterns) and 
            any(indicator in content for indicator in hobby_indicators)):
            type_scores["hobby"] = 0.75
        
        # General preferences
        if any(word in content for word in ["좋아해", "선호", "관심", "즐겨", "싫어"]):
            type_scores["preference"] = 0.7
        
        # Context-based adjustments
        if context_memories:
            context_types = [mem.get("type", "") for mem in context_memories]
            # If user has many identity memories, lower identity score for new messages
            if context_types.count("identity") > 2 and "identity" in type_scores:
                type_scores["identity"] *= 0.8
        
        if type_scores:
            best_type = max(type_scores.items(), key=lambda x: x[1])
            return {
                "tool_name": "classify_memory_type",
                "memory_type": best_type[0],
                "confidence": best_type[1],
                "all_scores": type_scores,
                "reasoning": f"Highest confidence: {best_type[0]} ({best_type[1]:.1%})",
                "context_influence": len(context_memories) if context_memories else 0
            }
        else:
            return {
                "tool_name": "classify_memory_type",
                "memory_type": "fact",
                "confidence": 0.5,
                "reasoning": "No strong type indicators, defaulting to fact",
                "context_influence": 0
            }
    
    async def analyze_user_patterns_tool(self, user_id: str, session_id: str = None) -> Dict[str, Any]:
        """
        TOOL: Analyze user's memory patterns and behavior
        React agent can use this to adapt its behavior to the user
        """
        memories = await self.storage.get_user_memories(user_id, session_id, limit=50)
        
        type_counts = {}
        importance_levels = []
        topics = set()
        temporal_patterns = []
        
        for memory in memories:
            # Type distribution
            type_str = memory.type.value
            type_counts[type_str] = type_counts.get(type_str, 0) + 1
            
            # Importance analysis
            importance_levels.append(memory.importance)
            
            # Topic extraction
            content_lower = memory.content.lower()
            if any(tech in content_lower for tech in ["파이썬", "자바", "프로그래밍"]):
                topics.add("프로그래밍")
            if any(work in content_lower for work in ["개발", "프로젝트", "회사"]):
                topics.add("업무")
            if any(hobby in content_lower for hobby in ["등산", "독서", "여행"]):
                topics.add("취미")
            if any(goal in content_lower for goal in ["목표", "계획", "하고싶"]):
                topics.add("목표")
            
            # Temporal patterns
            temporal_patterns.append({
                "timestamp": memory.timestamp,
                "importance": memory.importance,
                "type": memory.type.value
            })
        
        avg_importance = sum(importance_levels) / len(importance_levels) if importance_levels else 5.0
        dominant_type = max(type_counts.items(), key=lambda x: x[1])[0] if type_counts else None
        
        # Calculate user characteristics
        memory_velocity = len([p for p in temporal_patterns if (temporal_patterns[-1]["timestamp"] - p["timestamp"]).days <= 7]) if temporal_patterns else 0
        quality_score = sum(1 for imp in importance_levels if imp >= 7.0) / len(importance_levels) if importance_levels else 0
        
        return {
            "tool_name": "analyze_user_patterns",
            "total_memories": len(memories),
            "type_distribution": type_counts,
            "dominant_type": dominant_type,
            "average_importance": round(avg_importance, 2),
            "topics": list(topics),
            "user_maturity": "high" if len(memories) > 20 else "medium" if len(memories) > 5 else "low",
            "memory_velocity": memory_velocity,  # memories per week
            "quality_score": round(quality_score, 2),
            "insights": [
                f"User has {len(memories)} memories stored",
                f"Most common type: {dominant_type}" if dominant_type else "No dominant pattern",
                f"Average importance: {avg_importance:.1f}/10",
                f"Active topics: {', '.join(list(topics)[:3])}" if topics else "No clear topics",
                f"Quality score: {quality_score:.1%}"
            ]
        }
    
    async def calculate_contextual_importance_tool(self, base_importance: float, 
                                                  user_patterns: Dict, message_type: str) -> Dict[str, Any]:
        """
        TOOL: Calculate importance adjusted for user context
        React agent can use this to make final storage decisions
        """
        adjusted_importance = base_importance
        adjustments = []
        
        # New user boost
        total_memories = user_patterns.get("total_memories", 0)
        if total_memories < 5:
            adjusted_importance += 1.5
            adjustments.append("New user boost (+1.5)")
        elif total_memories < 10:
            adjusted_importance += 0.5
            adjustments.append("Early user boost (+0.5)")
        
        # Quality-based adjustments
        quality_score = user_patterns.get("quality_score", 0)
        if quality_score < 0.3:  # User stores low-quality info
            adjusted_importance += 0.5
            adjustments.append("Low quality history boost (+0.5)")
        
        # Rare type boost
        type_distribution = user_patterns.get("type_distribution", {})
        current_type_count = type_distribution.get(message_type, 0)
        if current_type_count == 0:
            adjusted_importance += 1.0
            adjustments.append(f"First {message_type} memory (+1.0)")
        elif current_type_count < 2:
            adjusted_importance += 0.5
            adjustments.append(f"Rare {message_type} type (+0.5)")
        
        # Critical types minimum
        if message_type in ["identity", "profession"]:
            adjusted_importance = max(adjusted_importance, 8.0)
            adjustments.append(f"Critical type minimum (8.0)")
        
        # User engagement boost
        memory_velocity = user_patterns.get("memory_velocity", 0)
        if memory_velocity > 5:  # Very active user
            adjusted_importance += 0.3
            adjustments.append("High engagement boost (+0.3)")
        
        final_importance = min(10.0, adjusted_importance)
        
        return {
            "tool_name": "calculate_contextual_importance",
            "original_importance": base_importance,
            "adjusted_importance": final_importance,
            "adjustments": adjustments,
            "reasoning": f"Adjusted from {base_importance} to {final_importance}",
            "boost_applied": final_importance > base_importance,
            "user_context": {
                "total_memories": total_memories,
                "quality_score": quality_score,
                "memory_velocity": memory_velocity,
                "type_rarity": current_type_count
            }
        }
    
    async def extract_entities_tool(self, message: str) -> Dict[str, Any]:
        """
        TOOL: Extract structured entities from message
        React agent can use this for detailed information parsing
        """
        extracted = self.intelligence.extract_key_information(message)
        
        return {
            "tool_name": "extract_entities",
            "entities": extracted.get("entities", {}),
            "topics": extracted.get("topics", []),
            "sentiment": extracted.get("sentiment", "neutral"),
            "relationships": extracted.get("relationships", []),
            "entity_count": len(extracted.get("entities", {})),
            "extraction_confidence": self._calculate_extraction_confidence(extracted)
        }
    
    def _calculate_relevance(self, query: str, content: str) -> float:
        """Calculate relevance score between query and content"""
        query_words = set(query.lower().split())
        content_words = set(content.lower().split())
        
        if not query_words:
            return 0.0
        
        intersection = query_words.intersection(content_words)
        return len(intersection) / len(query_words)
    
    def _calculate_extraction_confidence(self, extracted: Dict) -> float:
        """Calculate confidence in entity extraction"""
        entity_count = len(extracted.get("entities", {}))
        topic_count = len(extracted.get("topics", []))
        has_sentiment = extracted.get("sentiment") != "neutral"
        
        confidence = 0.0
        if entity_count > 0:
            confidence += min(0.5, entity_count * 0.2)
        if topic_count > 0:
            confidence += min(0.3, topic_count * 0.1)
        if has_sentiment:
            confidence += 0.2
        
        return min(1.0, confidence)