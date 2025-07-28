"""
Hierarchical Memory Type System
Provides multi-level classification for better organization
"""

from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
import re

@dataclass
class MemoryClassification:
    """Result of hierarchical classification"""
    major: str  # 대분류
    minor: str  # 중분류
    detail: str  # 소분류
    confidence: float
    
    def to_path(self) -> str:
        """Return as path format: personal/identity/name"""
        return f"{self.major}/{self.minor}/{self.detail}"
    
    def to_dict(self) -> Dict[str, str]:
        return {
            "major": self.major,
            "minor": self.minor,
            "detail": self.detail,
            "path": self.to_path(),
            "confidence": self.confidence
        }

class HierarchicalMemoryType:
    """계층적 메모리 타입 시스템"""
    
    def __init__(self):
        # Define hierarchical structure
        self.type_tree = {
            "personal": {
                "identity": {
                    "name": ["이름", "성함", "호칭", "name", "called"],
                    "age": ["나이", "살", "세", "출생", "age", "born"],
                    "location": ["살고", "거주", "위치", "주소", "사는", "live", "location"],
                    "gender": ["성별", "남자", "여자", "gender"],
                    "family": ["가족", "부모", "형제", "자녀", "family"]
                },
                "preference": {
                    "food": ["먹는", "음식", "좋아하는", "싫어하는", "food", "eat", "taste"],
                    "music": ["음악", "노래", "듣는", "music", "song"],
                    "activity": ["운동", "취미", "활동", "즐기는", "hobby", "activity"],
                    "style": ["스타일", "패션", "옷", "style", "fashion"],
                    "general": ["좋아", "싫어", "선호", "like", "dislike", "prefer"]
                },
                "profession": {
                    "job": ["직업", "일", "업무", "job", "work", "occupation"],
                    "company": ["회사", "직장", "근무", "company", "office"],
                    "role": ["역할", "직책", "담당", "role", "position", "title"],
                    "career": ["경력", "경험", "career", "experience"],
                    "education": ["학교", "전공", "졸업", "education", "study"]
                }
            },
            "knowledge": {
                "fact": {
                    "general": ["사실", "정보", "알고", "fact", "information"],
                    "specific": ["구체적", "정확한", "specific", "exact"],
                    "historical": ["과거", "역사", "예전", "history", "past"],
                    "current": ["현재", "지금", "최근", "current", "now"]
                },
                "skill": {
                    "technical": ["기술", "프로그래밍", "개발", "코딩", "tech", "programming"],
                    "language": ["언어", "영어", "한국어", "language", "speak"],
                    "soft": ["소통", "리더십", "협업", "communication", "leadership"],
                    "tool": ["도구", "사용", "프로그램", "tool", "software"]
                },
                "experience": {
                    "work": ["프로젝트", "업무", "일했", "project", "worked"],
                    "personal": ["경험", "했던", "기억", "experience", "memory"],
                    "achievement": ["성과", "달성", "이뤘", "achievement", "accomplished"],
                    "learning": ["배운", "학습", "공부", "learned", "studied"]
                }
            },
            "temporal": {
                "conversation": {
                    "question": ["?", "뭐", "어떻게", "왜", "언제", "what", "how", "why"],
                    "statement": ["입니다", "해요", "했어요", "is", "are", "was"],
                    "greeting": ["안녕", "반가", "hello", "hi"],
                    "response": ["네", "아니", "응답", "yes", "no", "response"]
                },
                "context": {
                    "current": ["지금", "오늘", "현재", "now", "today", "current"],
                    "past": ["어제", "예전", "과거", "yesterday", "before", "past"],
                    "future": ["내일", "나중", "계획", "tomorrow", "later", "plan"],
                    "session": ["방금", "아까", "just", "recently"]
                }
            }
        }
        
        # Build reverse mapping for faster lookup
        self._build_keyword_map()
    
    def _build_keyword_map(self):
        """Build keyword to path mapping for faster classification"""
        self.keyword_map = {}
        
        for major, minors in self.type_tree.items():
            for minor, details in minors.items():
                for detail, keywords in details.items():
                    path = f"{major}/{minor}/{detail}"
                    for keyword in keywords:
                        if keyword not in self.keyword_map:
                            self.keyword_map[keyword] = []
                        self.keyword_map[keyword].append(path)
    
    def classify(self, content: str, context: Optional[Dict[str, Any]] = None) -> MemoryClassification:
        """계층적 분류 수행"""
        content_lower = content.lower()
        
        # Score each possible classification
        path_scores = {}
        
        # Check keywords
        for keyword, paths in self.keyword_map.items():
            if keyword in content_lower:
                for path in paths:
                    if path not in path_scores:
                        path_scores[path] = 0
                    # Weight by keyword length and position
                    weight = len(keyword) / 10  # Longer keywords are more specific
                    if content_lower.startswith(keyword):
                        weight *= 2  # Boost if at start
                    path_scores[path] += weight
        
        # Apply context boosts
        if context:
            self._apply_context_boosts(path_scores, context)
        
        # Find best match
        if path_scores:
            best_path = max(path_scores.items(), key=lambda x: x[1])
            major, minor, detail = best_path[0].split('/')
            confidence = min(best_path[1] / 3.0, 1.0)  # Normalize confidence
            
            return MemoryClassification(major, minor, detail, confidence)
        
        # Default classification
        if "?" in content:
            return MemoryClassification("temporal", "conversation", "question", 0.8)
        elif len(content.split()) < 10:
            return MemoryClassification("temporal", "conversation", "statement", 0.5)
        else:
            return MemoryClassification("knowledge", "fact", "general", 0.3)
    
    def _apply_context_boosts(self, path_scores: Dict[str, float], context: Dict[str, Any]):
        """Apply contextual boosts to scores"""
        # Boost based on previous classifications
        if "previous_type" in context:
            prev_path = context["previous_type"]
            if prev_path in path_scores:
                path_scores[prev_path] *= 1.5
        
        # Boost based on session pattern
        if "session_types" in context:
            for session_type in context["session_types"]:
                if session_type in path_scores:
                    path_scores[session_type] *= 1.2
    
    def get_importance(self, classification: MemoryClassification) -> float:
        """Get importance score based on classification"""
        importance_map = {
            "personal/identity": 9.0,
            "personal/profession": 8.5,
            "knowledge/skill/technical": 8.0,
            "personal/preference": 7.0,
            "knowledge/experience": 7.0,
            "knowledge/fact": 6.0,
            "temporal/context": 4.0,
            "temporal/conversation": 3.0
        }
        
        # Check exact path first
        path = f"{classification.major}/{classification.minor}"
        if path in importance_map:
            return importance_map[path]
        
        # Check major category
        major_importance = {
            "personal": 7.0,
            "knowledge": 6.0,
            "temporal": 4.0
        }
        
        base = major_importance.get(classification.major, 5.0)
        # Adjust by confidence
        return base + (classification.confidence * 2.0)
    
    def get_storage_strategy(self, classification: MemoryClassification) -> Dict[str, Any]:
        """Determine storage strategy based on classification"""
        strategies = {
            "temporal/conversation": {
                "use_rag": True,
                "use_embedding": True,
                "ttl": None,  # Keep indefinitely
                "index_for_search": True
            },
            "personal/identity": {
                "use_rag": False,
                "use_embedding": True,
                "ttl": None,
                "index_for_search": True,
                "high_importance": True
            },
            "knowledge/skill": {
                "use_rag": True,
                "use_embedding": True,
                "ttl": None,
                "index_for_search": True
            },
            "temporal/context": {
                "use_rag": False,
                "use_embedding": False,
                "ttl": 86400,  # 24 hours
                "index_for_search": False
            }
        }
        
        path = f"{classification.major}/{classification.minor}"
        return strategies.get(path, {
            "use_rag": False,
            "use_embedding": True,
            "ttl": None,
            "index_for_search": True
        })
    
    def get_related_types(self, classification: MemoryClassification) -> List[str]:
        """Get related memory types for enhanced retrieval"""
        relations = {
            "personal/identity/name": ["personal/identity/age", "personal/identity/location"],
            "personal/profession/job": ["knowledge/skill/technical", "knowledge/experience/work"],
            "knowledge/skill/technical": ["knowledge/experience/work", "personal/profession/job"],
            "temporal/conversation/question": ["temporal/conversation/response", "temporal/context/current"]
        }
        
        path = classification.to_path()
        related = relations.get(path, [])
        
        # Always include parent categories
        related.append(f"{classification.major}/{classification.minor}")
        
        return list(set(related))