"""Memory Intelligence Layer for Smart Classification and Storage Decisions"""

from typing import Dict, List, Any
from .memory_types import MemoryType, Memory

class MemoryIntelligence:
    """Intelligence layer for memory classification and importance scoring"""
    
    @staticmethod
    def should_store(message: str, context: Dict[str, Any] = None) -> bool:
        """
        Intelligent decision on whether to store a message
        Uses comprehensive pattern analysis
        """
        if not message or len(message.strip()) < 5:
            return False
        
        # High-priority patterns (definitely store)
        high_priority_patterns = [
            "저는", "제가",           # Identity
            "개발자", "엔지니어",      # Profession
            "목표", "계획",          # Goals
            "프로젝트", "경험"        # Experience
        ]
        
        # Medium-priority patterns (likely store)
        medium_priority_patterns = [
            "좋아해", "선호",         # Preferences
            "취미", "관심",          # Hobbies
            "파이썬", "자바",        # Skills
            "회사", "업무",          # Work
            "팀", "동료"            # Professional context
        ]
        
        # Low-priority patterns (context-dependent)
        low_priority_patterns = [
            "생각해", "느껴",         # Opinions
            "배워", "공부",          # Learning
            "시간", "날짜"           # Temporal
        ]
        
        message_lower = message.lower()
        
        # Check high priority patterns
        if any(pattern in message_lower for pattern in high_priority_patterns):
            return True
        
        # Check medium priority patterns with additional context
        medium_matches = sum(1 for pattern in medium_priority_patterns if pattern in message_lower)
        if medium_matches >= 1:
            # Store if message has enough content
            if len(message.split()) >= 5:  # At least 5 words
                return True
        
        # Check low priority with multiple indicators
        low_matches = sum(1 for pattern in low_priority_patterns if pattern in message_lower)
        if low_matches >= 2 and len(message.split()) >= 8:  # Multiple indicators + substantial content
            return True
        
        # Context-based decisions
        if context:
            user_memory_count = context.get("user_memory_count", 0)
            # Be more permissive for new users
            if user_memory_count < 5 and medium_matches > 0:
                return True
        
        return False
    
    @staticmethod
    def extract_memory_type(message: str, context: Dict[str, Any] = None) -> MemoryType:
        """
        Intelligent memory type classification based on content analysis
        """
        content = message.lower()
        
        # Identity patterns (highest priority)
        identity_patterns = ["저는", "제가", "이름", "호출"]
        if any(pattern in content for pattern in identity_patterns):
            return MemoryType.IDENTITY
        
        # Professional patterns
        profession_patterns = ["개발자", "엔지니어", "직업", "회사", "업무", "팀장", "매니저"]
        if any(pattern in content for pattern in profession_patterns):
            return MemoryType.PROFESSION
        
        # Technical skills
        skill_patterns = ["파이썬", "자바", "자바스크립트", "프로그래밍", "코딩", "기술", "언어", "프레임워크"]
        if any(pattern in content for pattern in skill_patterns):
            return MemoryType.SKILL
        
        # Professional experience
        experience_patterns = ["프로젝트", "경험", "작업", "개발", "구현", "설계"]
        if any(pattern in content for pattern in experience_patterns):
            return MemoryType.EXPERIENCE
        
        # Goals and aspirations
        goal_patterns = ["목표", "계획", "하고싶", "되고싶", "꿈", "바라", "원해"]
        if any(pattern in content for pattern in goal_patterns):
            return MemoryType.GOAL
        
        # Hobbies (specific activities)
        hobby_indicators = ["등산", "독서", "여행", "음악", "운동", "게임"]
        hobby_patterns = ["취미", "즐겨", "좋아해"]
        if (any(pattern in content for pattern in hobby_patterns) and 
            any(indicator in content for indicator in hobby_indicators)):
            return MemoryType.HOBBY
        
        # General preferences
        preference_patterns = ["좋아해", "선호", "관심", "즐겨", "싫어", "선호도"]
        if any(pattern in content for pattern in preference_patterns):
            return MemoryType.PREFERENCE
        
        # Conversation patterns - questions and general chat
        question_patterns = ["어때", "어떻게", "뭐", "무엇", "누구", "언제", "어디", "왜", "어떤", "얼마", "몇", "?"]
        conversation_patterns = ["안녕", "고마워", "감사", "미안", "죄송", "네", "아니", "응", "그래"]
        if any(pattern in content for pattern in question_patterns + conversation_patterns):
            return MemoryType.CONVERSATION
        
        # Default to CONVERSATION for short messages that don't fit other categories
        if len(message.split()) < 10:
            return MemoryType.CONVERSATION
        
        # Default to FACT for longer informational content
        return MemoryType.FACT
    
    @staticmethod
    def calculate_importance(message: str, memory_type: MemoryType, context: Dict[str, Any] = None) -> float:
        """
        Calculate importance score based on content, type, and context
        Scale: 0.0 (not important) to 10.0 (extremely important)
        """
        # Base importance by memory type
        base_importance = {
            MemoryType.IDENTITY: 9.0,        # Core identity information
            MemoryType.PROFESSION: 8.5,      # Professional information
            MemoryType.GOAL: 8.0,           # Personal/professional goals
            MemoryType.SKILL: 7.5,          # Technical skills
            MemoryType.EXPERIENCE: 7.0,     # Work experience
            MemoryType.PREFERENCE: 6.5,     # Personal preferences
            MemoryType.HOBBY: 6.0,          # Hobbies and interests
            MemoryType.FACT: 5.0,           # General facts
            MemoryType.CONTEXT: 4.0,        # Contextual information
            MemoryType.CONVERSATION: 3.0     # Conversation history
        }
        
        importance = base_importance.get(memory_type, 5.0)
        
        # Content-based adjustments
        message_lower = message.lower()
        
        # Boost for detailed information
        word_count = len(message.split())
        if word_count > 15:
            importance += 1.0  # Detailed information is more valuable
        elif word_count > 10:
            importance += 0.5
        
        # Boost for specific details
        specific_indicators = ["구체적", "자세히", "정확히", "특히", "주로", "전문"]
        if any(indicator in message_lower for indicator in specific_indicators):
            importance += 0.5
        
        # Boost importance for questions (they need answers)
        if memory_type == MemoryType.CONVERSATION:
            question_indicators = ["?", "어때", "어떻게", "뭐", "무엇", "질문", "물어"]
            if any(indicator in message_lower for indicator in question_indicators):
                importance += 2.0  # Questions are more important to remember
        
        # Boost for current/recent information
        temporal_indicators = ["현재", "지금", "최근", "요즘", "오늘", "이번"]
        if any(indicator in message_lower for indicator in temporal_indicators):
            importance += 0.5
        
        # Context-based adjustments
        if context:
            user_memory_count = context.get("user_memory_count", 0)
            
            # Boost early memories for new users
            if user_memory_count < 5:
                importance += 1.0
            elif user_memory_count < 10:
                importance += 0.5
            
            # Check for rare memory types
            type_distribution = context.get("type_distribution", {})
            current_type_count = type_distribution.get(memory_type.value, 0)
            if current_type_count == 0:  # First of this type
                importance += 1.0
            elif current_type_count < 2:  # Rare type
                importance += 0.5
        
        # Ensure importance stays within bounds
        return min(10.0, max(0.0, importance))
    
    @staticmethod
    def extract_key_information(message: str) -> Dict[str, Any]:
        """
        Extract structured information from message
        Returns dictionary with extracted entities and relationships
        """
        extracted = {
            "entities": {},
            "relationships": [],
            "topics": [],
            "sentiment": "neutral"
        }
        
        message_lower = message.lower()
        
        # Extract names (improved Korean parsing)
        import re
        # Better name pattern that excludes grammatical particles
        name_patterns = [
            r"저는\s+([가-힣]+)이고",     # "저는 이지은이고" -> "이지은"
            r"저는\s+([가-힣]+)입니다",    # "저는 이지은입니다" -> "이지은"
            r"제\s+이름은\s+([가-힣]+)",   # "제 이름은 이지은"
            r"저는\s+([가-힣]+)\s*$"      # "저는 이지은" (end of sentence)
        ]
        
        for pattern in name_patterns:
            name_match = re.search(pattern, message)
            if name_match:
                extracted["entities"]["name"] = name_match.group(1)
                break
        
        # Extract technologies/skills
        tech_keywords = ["파이썬", "자바", "자바스크립트", "리액트", "텐서플로우", "pytorch"]
        found_tech = [tech for tech in tech_keywords if tech in message_lower]
        if found_tech:
            extracted["entities"]["technologies"] = found_tech
        
        # Extract hobbies/activities
        hobby_keywords = ["등산", "독서", "여행", "음악", "운동", "게임", "요리"]
        found_hobbies = [hobby for hobby in hobby_keywords if hobby in message_lower]
        if found_hobbies:
            extracted["entities"]["hobbies"] = found_hobbies
        
        # Extract company/workplace
        company_pattern = r"([가-힣A-Za-z]+)에서\s+(?:일|근무|개발)"
        company_match = re.search(company_pattern, message)
        if company_match:
            extracted["entities"]["company"] = company_match.group(1)
        
        # Determine topics
        if any(word in message_lower for word in ["개발", "프로그래밍", "코딩", "기술"]):
            extracted["topics"].append("프로그래밍")
        if any(word in message_lower for word in ["업무", "회사", "팀", "프로젝트"]):
            extracted["topics"].append("업무")
        if any(word in message_lower for word in ["취미", "여가", "즐겨"]):
            extracted["topics"].append("개인생활")
        
        # Simple sentiment analysis
        positive_words = ["좋아", "즐겨", "만족", "행복", "기뻐"]
        negative_words = ["싫어", "힘들", "어려", "문제", "스트레스"]
        
        positive_count = sum(1 for word in positive_words if word in message_lower)
        negative_count = sum(1 for word in negative_words if word in message_lower)
        
        if positive_count > negative_count:
            extracted["sentiment"] = "positive"
        elif negative_count > positive_count:
            extracted["sentiment"] = "negative"
        
        return extracted