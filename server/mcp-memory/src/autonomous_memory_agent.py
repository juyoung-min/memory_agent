"""
Truly Autonomous Memory Agent
Intelligently manages memory operations without explicit instructions
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

from .memory_agent import MemoryAgent
from .memory_agent.enhanced_intelligence import EnhancedMemoryIntelligence
from .memory_agent.memory_types import MemoryType
from .storage_strategy import StorageStrategyDeterminer
from .vector_index_optimizer import MemorySearchOptimizer
from .clients import InternalMCPClient

logger = logging.getLogger(__name__)

class AutonomousMemoryAgent:
    """
    A truly autonomous memory agent that decides:
    - WHAT to remember
    - WHEN to retrieve
    - HOW to respond
    - WHETHER to store
    """
    
    def __init__(
        self,
        memory_agent: MemoryAgent,
        db_client: InternalMCPClient,
        model_client: InternalMCPClient,
        rag_client: InternalMCPClient
    ):
        self.memory_agent = memory_agent
        self.db_client = db_client
        self.model_client = model_client
        self.rag_client = rag_client
        
        # Enhanced components
        self.intelligence = EnhancedMemoryIntelligence()
        self.storage_strategy = StorageStrategyDeterminer()
        self.search_optimizer = MemorySearchOptimizer(db_client)
        
        # Context understanding
        self.conversation_buffer = {}  # user_id -> recent exchanges
        self.user_models = {}  # user_id -> learned patterns
        
    async def process_autonomously(
        self,
        user_id: str,
        message: str,
        session_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a message completely autonomously
        The agent decides everything based on context and content
        """
        start_time = datetime.utcnow()
        
        # Initialize response structure
        response = {
            "success": True,
            "user_id": user_id,
            "session_id": session_id,
            "decisions": {},
            "actions_taken": []
        }
        
        try:
            # 1. UNDERSTAND: Analyze the message deeply
            understanding = await self._understand_message(user_id, message, session_id)
            response["decisions"]["understanding"] = understanding
            
            # 2. DECIDE: What memory operations are needed?
            memory_plan = await self._decide_memory_operations(understanding, user_id)
            response["decisions"]["memory_plan"] = memory_plan
            
            # 3. RETRIEVE: Get relevant context (if needed)
            context = {}
            if memory_plan.get("needs_retrieval"):
                context = await self._intelligent_retrieval(
                    user_id,
                    understanding,
                    memory_plan.get("retrieval_strategy")
                )
                response["actions_taken"].append({
                    "action": "retrieval",
                    "items_found": len(context.get("memories", []))
                })
            
            # 4. RESPOND: Generate response (if needed)
            generated_response = None
            if memory_plan.get("needs_response"):
                generated_response = await self._generate_contextual_response(
                    message,
                    context,
                    understanding
                )
                response["response"] = generated_response
                response["actions_taken"].append({"action": "response_generation"})
            
            # 5. STORE: Save memories (if valuable)
            if memory_plan.get("should_store"):
                storage_results = await self._intelligent_storage(
                    user_id,
                    session_id,
                    message,
                    understanding,
                    memory_plan.get("storage_strategy"),
                    generated_response
                )
                response["actions_taken"].extend(storage_results)
            
            # 6. LEARN: Update user model
            await self._update_user_model(user_id, understanding, memory_plan)
            
            # Performance metrics
            response["performance"] = {
                "duration_ms": (datetime.utcnow() - start_time).total_seconds() * 1000,
                "decisions_made": len(response["decisions"]),
                "actions_taken": len(response["actions_taken"])
            }
            
            return response
            
        except Exception as e:
            logger.error(f"Error in autonomous processing: {e}", exc_info=True)
            response["success"] = False
            response["error"] = str(e)
            return response
    
    async def _understand_message(
        self,
        user_id: str,
        message: str,
        session_id: str
    ) -> Dict[str, Any]:
        """Deep understanding of message intent and context"""
        
        # Get recent conversation context
        recent_buffer = self.conversation_buffer.get(user_id, [])
        
        # Analyze message
        understanding = {
            "raw_message": message,
            "language": self._detect_language(message),
            "intent": self._analyze_intent(message, recent_buffer),
            "temporal_reference": self._detect_temporal_reference(message),
            "question_type": self._classify_question(message),
            "entities": self.intelligence._extract_entities(message),
            "sentiment": self._analyze_sentiment(message),
            "requires_memory": self._needs_memory_access(message),
            "conversation_continuity": self._check_continuity(message, recent_buffer)
        }
        
        # Classify memory type
        memory_type = self.intelligence.extract_memory_type(message, understanding)
        understanding["memory_type"] = memory_type.value
        
        # Process content
        processed = self.intelligence.process_content_for_storage(
            content=message,
            memory_type=memory_type,
            context=understanding
        )
        
        understanding["processed_content"] = {
            "importance": processed.importance,
            "should_store": processed.should_store,
            "keywords": processed.keywords,
            "summary": processed.summary
        }
        
        return understanding
    
    def _analyze_intent(self, message: str, recent_buffer: List) -> str:
        """Determine the primary intent of the message"""
        
        # Check for question patterns
        if "?" in message or any(q in message for q in ["뭐", "어떻게", "왜", "언제", "어디", "누구"]):
            # Asking about previous conversation
            if any(word in message for word in ["방금", "아까", "이전", "전에", "했", "말했"]):
                return "recall_previous"
            # General question
            return "question"
        
        # Information sharing
        if any(word in message for word in ["입니다", "예요", "이에요", "있어요"]):
            return "information_sharing"
        
        # Greeting
        if any(word in message for word in ["안녕", "반가워", "처음"]):
            return "greeting"
        
        # Default
        return "conversation"
    
    def _needs_memory_access(self, message: str) -> bool:
        """Determine if this message requires memory retrieval"""
        
        # Temporal references need memory
        temporal_words = ["방금", "아까", "이전", "전에", "어제", "지난", "예전"]
        if any(word in message for word in temporal_words):
            return True
        
        # Questions about self/user need memory
        self_references = ["내가", "제가", "나는", "저는", "우리"]
        question_words = ["뭐", "어떤", "어떻게", "누구", "언제"]
        
        has_self_ref = any(word in message for word in self_references)
        has_question = any(word in message for word in question_words)
        
        return has_self_ref and has_question
    
    async def _decide_memory_operations(
        self,
        understanding: Dict[str, Any],
        user_id: str
    ) -> Dict[str, Any]:
        """Decide what memory operations to perform"""
        
        plan = {
            "needs_retrieval": False,
            "needs_response": True,  # Usually generate response
            "should_store": False,
            "retrieval_strategy": None,
            "storage_strategy": None
        }
        
        # Decide based on intent
        intent = understanding["intent"]
        
        if intent == "recall_previous":
            # Need to retrieve recent conversation
            plan["needs_retrieval"] = True
            plan["retrieval_strategy"] = {
                "type": "temporal",
                "focus": "recent_conversation",
                "limit": 10
            }
            
        elif intent == "question" and understanding["requires_memory"]:
            # Need to search relevant memories
            plan["needs_retrieval"] = True
            plan["retrieval_strategy"] = {
                "type": "semantic",
                "focus": "relevant_context",
                "limit": 5
            }
        
        # Decide storage based on importance
        if understanding["processed_content"]["importance"] >= 4.0:
            plan["should_store"] = True
            plan["storage_strategy"] = self.storage_strategy.determine_strategy(
                memory_type=understanding["memory_type"],
                importance=understanding["processed_content"]["importance"],
                content_size=len(understanding["raw_message"])
            )
        
        # Learn from user patterns
        user_model = self.user_models.get(user_id, {})
        if user_model.get("prefers_brief_responses"):
            plan["response_style"] = "brief"
        
        return plan
    
    async def _intelligent_retrieval(
        self,
        user_id: str,
        understanding: Dict[str, Any],
        strategy: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Intelligently retrieve relevant memories"""
        
        context = {"memories": [], "total_context": 0}
        
        if not strategy:
            return context
        
        # Build smart query based on understanding
        if strategy["type"] == "temporal":
            # Get recent conversations
            query = understanding["raw_message"]
            memory_types = ["conversation"]
            
        elif strategy["type"] == "semantic":
            # Use keywords and entities for better search
            keywords = understanding["processed_content"]["keywords"]
            query = " ".join(keywords) if keywords else understanding["raw_message"]
            memory_types = None  # Search all types
        
        else:
            query = understanding["raw_message"]
            memory_types = None
        
        # Use optimized search
        search_result = await self.search_optimizer.optimized_search(
            table_name="user_memories",
            query_vector=await self._get_embedding(query),
            filters={
                "user_id": user_id,
                "memory_type": {"$in": memory_types} if memory_types else None
            },
            limit=strategy.get("limit", 5),
            optimize_for="accuracy" if understanding["intent"] == "recall_previous" else "balanced"
        )
        
        if search_result.get("success"):
            context["memories"] = search_result.get("results", [])
            context["total_context"] = len(context["memories"])
            context["retrieval_performance"] = search_result.get("performance")
        
        return context
    
    async def _generate_contextual_response(
        self,
        message: str,
        context: Dict[str, Any],
        understanding: Dict[str, Any]
    ) -> str:
        """Generate response with deep context understanding"""
        
        # Build context-aware prompt
        prompt_parts = []
        
        # Add relevant memories
        if context.get("memories"):
            prompt_parts.append("=== Relevant Context ===")
            
            # Group by type for better organization
            by_type = {}
            for mem in context["memories"]:
                mem_type = mem.get("memory_type", "other")
                if mem_type not in by_type:
                    by_type[mem_type] = []
                by_type[mem_type].append(mem)
            
            # Add conversations first (most relevant for recall)
            if "conversation" in by_type:
                prompt_parts.append("\nRecent Conversations:")
                for conv in by_type["conversation"][:5]:
                    prompt_parts.append(f"- {conv['content']}")
            
            # Add other relevant information
            for mem_type, memories in by_type.items():
                if mem_type != "conversation":
                    prompt_parts.append(f"\n{mem_type.title()} Information:")
                    for mem in memories[:3]:
                        prompt_parts.append(f"- {mem['content']}")
        
        # Add understanding context
        prompt_parts.append(f"\n=== Current Interaction ===")
        prompt_parts.append(f"User Message: {message}")
        prompt_parts.append(f"Detected Intent: {understanding['intent']}")
        prompt_parts.append(f"Language: {understanding['language']}")
        
        # Intent-specific instructions
        instructions = self._get_response_instructions(understanding)
        prompt_parts.append(f"\n=== Instructions ===")
        prompt_parts.append(instructions)
        
        full_prompt = "\n".join(prompt_parts)
        
        # Generate response
        response = await self.model_client.call_tool(
            "generate_completion",
            {
                "prompt": full_prompt,
                "model": "EXAONE-3.5-2.4B-Instruct",
                "temperature": 0.7,
                "max_tokens": 300
            }
        )
        
        return response.get("text", "I understand. Let me help you with that.")
    
    def _get_response_instructions(self, understanding: Dict[str, Any]) -> str:
        """Get specific instructions based on intent"""
        
        intent = understanding["intent"]
        lang = understanding["language"]
        
        if intent == "recall_previous":
            return f"""
1. Look at the Recent Conversations section carefully
2. Find what the user is asking about (their previous question or statement)
3. Answer specifically what they asked before
4. Use the same language ({lang}) as the user
5. Be precise - quote their exact previous message if relevant
"""
        
        elif intent == "question":
            return f"""
1. Answer the user's question using the provided context
2. Be accurate and specific
3. Use the same language ({lang}) as the user
4. If you don't have enough information, say so honestly
"""
        
        else:
            return f"""
1. Respond naturally to the user's message
2. Use the context to personalize your response
3. Use the same language ({lang}) as the user
4. Be helpful and conversational
"""
    
    async def _intelligent_storage(
        self,
        user_id: str,
        session_id: str,
        message: str,
        understanding: Dict[str, Any],
        strategy: Dict[str, Any],
        response: Optional[str]
    ) -> List[Dict[str, Any]]:
        """Store memories intelligently based on value and context"""
        
        actions = []
        
        # Store user message if valuable
        if understanding["processed_content"]["should_store"]:
            # Use processed content for storage
            content = understanding["processed_content"].get("structured_content", message)
            
            result = await self.memory_agent.add_memory(
                user_id=user_id,
                session_id=session_id,
                content=content,
                memory_type=understanding["memory_type"],
                importance=understanding["processed_content"]["importance"],
                metadata={
                    "original": message,
                    "keywords": understanding["processed_content"]["keywords"],
                    "entities": understanding["entities"],
                    "intent": understanding["intent"],
                    "processed": True
                }
            )
            
            actions.append({
                "action": "store_user_message",
                "memory_id": result.get("memory_id"),
                "type": understanding["memory_type"],
                "importance": understanding["processed_content"]["importance"]
            })
        
        # Store response if it contains valuable information
        if response and len(response) > 20:
            # Quick analysis of response value
            response_importance = 5.0  # Base importance
            
            # Higher importance if answering a recall question
            if understanding["intent"] == "recall_previous":
                response_importance = 7.0
            
            if response_importance >= 4.0:
                response_result = await self.memory_agent.add_memory(
                    user_id=user_id,
                    session_id=session_id,
                    content=f"Assistant: {response}",
                    memory_type="conversation",
                    importance=response_importance,
                    metadata={
                        "role": "assistant",
                        "in_response_to": understanding.get("intent"),
                        "context_used": understanding.get("requires_memory", False)
                    }
                )
                
                actions.append({
                    "action": "store_response",
                    "memory_id": response_result.get("memory_id"),
                    "importance": response_importance
                })
        
        # Update conversation buffer
        if user_id not in self.conversation_buffer:
            self.conversation_buffer[user_id] = []
        
        self.conversation_buffer[user_id].append({
            "message": message,
            "response": response,
            "timestamp": datetime.utcnow(),
            "understanding": understanding["intent"]
        })
        
        # Keep only recent conversations in buffer
        if len(self.conversation_buffer[user_id]) > 10:
            self.conversation_buffer[user_id] = self.conversation_buffer[user_id][-10:]
        
        return actions
    
    async def _update_user_model(
        self,
        user_id: str,
        understanding: Dict[str, Any],
        plan: Dict[str, Any]
    ):
        """Learn from user interactions to improve future responses"""
        
        if user_id not in self.user_models:
            self.user_models[user_id] = {
                "interaction_count": 0,
                "common_intents": {},
                "language_preference": understanding["language"],
                "avg_message_length": 0,
                "question_frequency": 0
            }
        
        model = self.user_models[user_id]
        
        # Update statistics
        model["interaction_count"] += 1
        
        # Track intent patterns
        intent = understanding["intent"]
        if intent not in model["common_intents"]:
            model["common_intents"][intent] = 0
        model["common_intents"][intent] += 1
        
        # Update averages
        current_length = len(understanding["raw_message"])
        model["avg_message_length"] = (
            (model["avg_message_length"] * (model["interaction_count"] - 1) + current_length) /
            model["interaction_count"]
        )
        
        # Track question frequency
        if understanding["intent"] in ["question", "recall_previous"]:
            model["question_frequency"] = (
                (model["question_frequency"] * (model["interaction_count"] - 1) + 1) /
                model["interaction_count"]
            )
        
        # Detect preferences
        if model["avg_message_length"] < 50:
            model["prefers_brief_responses"] = True
        
        logger.debug(f"Updated user model for {user_id}: {model}")
    
    def _detect_language(self, message: str) -> str:
        """Detect the language of the message"""
        # Simple detection based on character sets
        if any('\u3131' <= char <= '\u318E' or '\uAC00' <= char <= '\uD7A3' for char in message):
            return "Korean"
        return "English"
    
    def _detect_temporal_reference(self, message: str) -> Optional[str]:
        """Detect temporal references in the message"""
        temporal_patterns = {
            "just_now": ["방금", "지금", "막"],
            "recent": ["아까", "조금 전", "이전"],
            "yesterday": ["어제", "어젯"],
            "past": ["예전", "과거", "옛날"]
        }
        
        for time_type, patterns in temporal_patterns.items():
            if any(pattern in message for pattern in patterns):
                return time_type
        
        return None
    
    def _classify_question(self, message: str) -> Optional[str]:
        """Classify the type of question being asked"""
        if "?" not in message and not any(q in message for q in ["뭐", "어떤", "어떻게"]):
            return None
        
        # What questions
        if any(word in message for word in ["뭐", "무엇", "what"]):
            return "what"
        # Who questions
        elif any(word in message for word in ["누구", "누가", "who"]):
            return "who"
        # When questions
        elif any(word in message for word in ["언제", "when"]):
            return "when"
        # Where questions
        elif any(word in message for word in ["어디", "where"]):
            return "where"
        # How questions
        elif any(word in message for word in ["어떻게", "how"]):
            return "how"
        # Why questions
        elif any(word in message for word in ["왜", "why"]):
            return "why"
        
        return "general"
    
    def _analyze_sentiment(self, message: str) -> str:
        """Simple sentiment analysis"""
        positive_words = ["좋아", "감사", "고마워", "행복", "기뻐", "최고"]
        negative_words = ["싫어", "나빠", "슬퍼", "화나", "짜증", "최악"]
        
        pos_count = sum(1 for word in positive_words if word in message)
        neg_count = sum(1 for word in negative_words if word in message)
        
        if pos_count > neg_count:
            return "positive"
        elif neg_count > pos_count:
            return "negative"
        return "neutral"
    
    def _check_continuity(self, message: str, recent_buffer: List) -> float:
        """Check if this message continues a previous conversation"""
        if not recent_buffer:
            return 0.0
        
        # Check for pronouns or references
        continuity_markers = ["그래서", "그런데", "그리고", "또", "아", "그거"]
        
        if any(marker in message for marker in continuity_markers):
            return 0.8
        
        # Check for topic similarity with recent messages
        # (Simplified - could use embeddings for better similarity)
        recent_keywords = set()
        for recent in recent_buffer[-3:]:
            if "keywords" in recent.get("understanding", {}):
                recent_keywords.update(recent["understanding"]["keywords"])
        
        current_words = set(message.split())
        overlap = len(recent_keywords & current_words)
        
        if overlap > 2:
            return 0.6
        elif overlap > 0:
            return 0.3
        
        return 0.0
    
    async def _get_embedding(self, text: str) -> List[float]:
        """Get embedding for text"""
        response = await self.rag_client.call_tool(
            "rag_generate_embedding",
            {"text": text, "model": "bge-m3"}
        )
        return response.get("embedding", [])