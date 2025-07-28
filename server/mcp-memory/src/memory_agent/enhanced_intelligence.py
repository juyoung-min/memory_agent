"""
Enhanced Memory Intelligence Layer
Processes and structures content before storage
"""

import json
import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass

from .memory_types import MemoryType
from .hierarchical_memory_types import HierarchicalMemoryType, MemoryClassification

@dataclass
class ProcessedContent:
    """Result of content processing"""
    structured_content: str
    extracted_entities: List[Dict[str, Any]]
    summary: Optional[str]
    keywords: List[str]
    should_store: bool
    storage_format: str  # 'full', 'structured', 'json', 'summary'
    importance: float
    metadata: Dict[str, Any]

class EnhancedMemoryIntelligence:
    """Enhanced intelligence for memory processing"""
    
    def __init__(self):
        self.hierarchical_types = HierarchicalMemoryType()
        # Korean entity patterns
        self.entity_patterns = {
            "name": r"(?:제 이름은|저는|나는)\s*([가-힣]{2,5})(?:입니다|예요|이에요)",
            "age": r"(\d{1,3})(?:살|세)(?:입니다|예요|이에요)?",
            "location": r"(?:서울|부산|대구|인천|광주|대전|울산|경기|강원|충북|충남|전북|전남|경북|경남|제주)(?:에서?|에\s*살|에\s*거주)",
            "company": r"(?:회사는|직장은|근무하는 곳은)\s*([가-힣A-Za-z\s]+)(?:입니다|예요|이에요)",
            "skill": r"(?:할 수 있|사용할 수 있|잘하는|전문)\s*(?:는|은)?\s*([가-힣A-Za-z\s,]+)(?:입니다|예요|이에요)?",
            "preference": r"(?:좋아하는|선호하는|즐기는)\s*(?:것은|건)?\s*([가-힣A-Za-z\s]+)(?:입니다|예요|이에요)?",
        }
        
    def process_content_for_storage(
        self, 
        content: str, 
        memory_type: MemoryType,
        context: Dict[str, Any]
    ) -> ProcessedContent:
        """Process content for intelligent storage"""
        
        # 1. Normalize content
        normalized = self._normalize_content(content)
        
        # 2. Extract base information
        entities = self._extract_entities(normalized)
        keywords = self._extract_keywords(normalized)
        
        # 3. Process based on memory type
        if memory_type == MemoryType.CONVERSATION:
            return self._process_conversation(normalized, entities, keywords, context)
        elif memory_type == MemoryType.FACT:
            return self._process_fact(normalized, entities, keywords, context)
        elif memory_type == MemoryType.PREFERENCE:
            return self._process_preference(normalized, entities, keywords, context)
        elif memory_type == MemoryType.IDENTITY:
            return self._process_identity(normalized, entities, keywords, context)
        elif memory_type == MemoryType.SKILL:
            return self._process_skill(normalized, entities, keywords, context)
        elif memory_type == MemoryType.EXPERIENCE:
            return self._process_experience(normalized, entities, keywords, context)
        else:
            # Default processing
            return ProcessedContent(
                structured_content=normalized,
                extracted_entities=entities,
                summary=self._generate_summary(normalized),
                keywords=keywords,
                should_store=True,
                storage_format="full",
                importance=5.0,
                metadata={}
            )
    
    def _normalize_content(self, content: str) -> str:
        """Normalize and clean content"""
        # Remove extra whitespace
        content = re.sub(r'\s+', ' ', content.strip())
        
        # Fix common typos/variations
        replacements = {
            "되요": "돼요",
            "됬": "됐",
            "왠만": "웬만",
        }
        for old, new in replacements.items():
            content = content.replace(old, new)
        
        return content
    
    def _extract_entities(self, content: str) -> List[Dict[str, Any]]:
        """Extract named entities and structured information"""
        entities = []
        
        for entity_type, pattern in self.entity_patterns.items():
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                entities.append({
                    "type": entity_type,
                    "value": match.strip(),
                    "confidence": 0.8 if len(match) > 2 else 0.6
                })
        
        # Extract numbers, dates, emails, etc.
        # Numbers
        numbers = re.findall(r'\b\d+(?:\.\d+)?\b', content)
        for num in numbers:
            entities.append({
                "type": "number",
                "value": num,
                "confidence": 1.0
            })
        
        # Dates (Korean format)
        dates = re.findall(r'(\d{4}년\s*\d{1,2}월\s*\d{1,2}일)', content)
        for date in dates:
            entities.append({
                "type": "date",
                "value": date,
                "confidence": 0.9
            })
        
        return entities
    
    def _extract_keywords(self, content: str) -> List[str]:
        """Extract important keywords"""
        # Remove common words (Korean stop words)
        stop_words = {
            "는", "은", "이", "가", "을", "를", "에", "에서", "으로", "와", "과",
            "의", "하다", "있다", "되다", "수", "그", "저", "이것", "그것"
        }
        
        # Split into words
        words = content.split()
        
        # Filter keywords
        keywords = []
        for word in words:
            # Remove particles
            clean_word = re.sub(r'[은는이가을를에서]$', '', word)
            
            # Skip if too short or stop word
            if len(clean_word) < 2 or clean_word in stop_words:
                continue
                
            # Add if meaningful
            if re.search(r'[가-힣]{2,}|[A-Za-z]{3,}', clean_word):
                keywords.append(clean_word)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_keywords = []
        for kw in keywords:
            if kw not in seen:
                seen.add(kw)
                unique_keywords.append(kw)
        
        return unique_keywords[:10]  # Limit to top 10
    
    def _generate_summary(self, content: str, max_length: int = 100) -> str:
        """Generate concise summary"""
        if len(content) <= max_length:
            return content
        
        # Extract key sentences
        sentences = re.split(r'[.!?]+', content)
        if not sentences:
            return content[:max_length] + "..."
        
        # Prioritize sentences with important markers
        priority_markers = ["중요", "핵심", "주요", "특히", "꼭", "반드시"]
        
        for sentence in sentences:
            if any(marker in sentence for marker in priority_markers):
                return sentence.strip()[:max_length]
        
        # Return first sentence if no priority found
        return sentences[0].strip()[:max_length]
    
    def _process_conversation(
        self, 
        content: str, 
        entities: List[Dict],
        keywords: List[str],
        context: Dict
    ) -> ProcessedContent:
        """Process conversation memory"""
        
        # Check if it's a question
        is_question = "?" in content or any(q in content for q in ["뭐", "어떻게", "왜", "언제"])
        
        # For conversations, keep full context
        return ProcessedContent(
            structured_content=content,
            extracted_entities=entities,
            summary=self._generate_summary(content),
            keywords=keywords,
            should_store=True,  # Always store conversations
            storage_format="full",
            importance=7.0 if is_question else 5.0,
            metadata={
                "is_question": is_question,
                "response_needed": is_question
            }
        )
    
    def _process_fact(
        self, 
        content: str, 
        entities: List[Dict],
        keywords: List[str],
        context: Dict
    ) -> ProcessedContent:
        """Process fact memory"""
        
        # Create structured fact statement
        fact_statement = self._create_fact_statement(content, entities)
        
        # Facts should be concise and searchable
        return ProcessedContent(
            structured_content=fact_statement,
            extracted_entities=entities,
            summary=fact_statement,  # Facts are their own summary
            keywords=keywords,
            should_store=len(entities) > 0 or len(keywords) > 3,
            storage_format="structured",
            importance=self._calculate_fact_importance(entities, keywords),
            metadata={
                "fact_type": self._classify_fact_type(content),
                "confidence": self._calculate_confidence(entities)
            }
        )
    
    def _process_preference(
        self, 
        content: str, 
        entities: List[Dict],
        keywords: List[str],
        context: Dict
    ) -> ProcessedContent:
        """Process preference memory"""
        
        # Extract preference structure
        preference_data = self._extract_preference_structure(content)
        
        # Store as JSON for easy querying
        return ProcessedContent(
            structured_content=json.dumps(preference_data, ensure_ascii=False),
            extracted_entities=entities,
            summary=f"{preference_data.get('subject')}에 대한 선호도: {preference_data.get('preference_type')}",
            keywords=keywords,
            should_store=preference_data.get("preference_level") is not None,
            storage_format="json",
            importance=6.0 + (preference_data.get("preference_level", 0) / 10),
            metadata=preference_data
        )
    
    def _process_identity(
        self, 
        content: str, 
        entities: List[Dict],
        keywords: List[str],
        context: Dict
    ) -> ProcessedContent:
        """Process identity memory"""
        
        # Identity information should be highly structured
        identity_data = {
            "original": content,
            "attributes": {}
        }
        
        # Extract specific identity attributes
        for entity in entities:
            if entity["type"] in ["name", "age", "location"]:
                identity_data["attributes"][entity["type"]] = entity["value"]
        
        return ProcessedContent(
            structured_content=json.dumps(identity_data, ensure_ascii=False),
            extracted_entities=entities,
            summary=self._create_identity_summary(identity_data),
            keywords=keywords,
            should_store=len(identity_data["attributes"]) > 0,
            storage_format="json",
            importance=9.0,  # Identity is always important
            metadata=identity_data
        )
    
    def _process_skill(
        self, 
        content: str, 
        entities: List[Dict],
        keywords: List[str],
        context: Dict
    ) -> ProcessedContent:
        """Process skill memory"""
        
        # Extract skill levels and categories
        skill_data = self._extract_skill_structure(content)
        
        return ProcessedContent(
            structured_content=json.dumps(skill_data, ensure_ascii=False),
            extracted_entities=entities,
            summary=f"기술: {', '.join(skill_data.get('skills', []))}",
            keywords=keywords + skill_data.get('skills', []),
            should_store=len(skill_data.get('skills', [])) > 0,
            storage_format="json",
            importance=7.5,
            metadata=skill_data
        )
    
    def _process_experience(
        self, 
        content: str, 
        entities: List[Dict],
        keywords: List[str],
        context: Dict
    ) -> ProcessedContent:
        """Process experience memory"""
        
        # Experiences can be longer, but should be summarized
        summary = self._generate_summary(content, max_length=200)
        
        # Extract time references
        time_refs = self._extract_time_references(content)
        
        return ProcessedContent(
            structured_content=content,  # Keep full experience
            extracted_entities=entities,
            summary=summary,
            keywords=keywords,
            should_store=len(content.split()) > 10,  # Only significant experiences
            storage_format="full",
            importance=self._calculate_experience_importance(content, time_refs),
            metadata={
                "time_references": time_refs,
                "word_count": len(content.split())
            }
        )
    
    def _create_fact_statement(self, content: str, entities: List[Dict]) -> str:
        """Create concise fact statement"""
        # If entities exist, build around them
        if entities:
            main_entity = max(entities, key=lambda e: e["confidence"])
            return f"{main_entity['type']}: {main_entity['value']}"
        
        # Otherwise, extract key information
        # Remove question words and clean up
        fact = re.sub(r'[?.!]', '', content)
        fact = re.sub(r'^(저는|나는|제가)\s*', '', fact)
        
        return fact.strip()
    
    def _extract_preference_structure(self, content: str) -> Dict[str, Any]:
        """Extract structured preference data"""
        preference_data = {
            "subject": None,
            "preference_type": None,  # like, dislike, prefer
            "preference_level": None,  # 1-10
            "reason": None
        }
        
        # Positive preferences
        if any(word in content for word in ["좋아", "선호", "즐겨", "최고"]):
            preference_data["preference_type"] = "like"
            preference_data["preference_level"] = 8
        # Negative preferences
        elif any(word in content for word in ["싫어", "안좋아", "별로"]):
            preference_data["preference_type"] = "dislike"
            preference_data["preference_level"] = 3
        
        # Extract subject (what they like/dislike)
        subject_match = re.search(r'([\w\s]+)(?:을|를|이|가)\s*(?:좋아|싫어|선호)', content)
        if subject_match:
            preference_data["subject"] = subject_match.group(1).strip()
        
        return preference_data
    
    def _extract_skill_structure(self, content: str) -> Dict[str, Any]:
        """Extract structured skill data"""
        skill_data = {
            "skills": [],
            "level": None,
            "category": None
        }
        
        # Common skill keywords
        skill_keywords = ["Python", "Java", "JavaScript", "React", "Docker", "Kubernetes", 
                         "개발", "프로그래밍", "디자인", "분석", "관리", "영어", "중국어"]
        
        for keyword in skill_keywords:
            if keyword.lower() in content.lower():
                skill_data["skills"].append(keyword)
        
        # Extract level indicators
        if any(word in content for word in ["전문", "숙련", "고급"]):
            skill_data["level"] = "expert"
        elif any(word in content for word in ["중급", "경험"]):
            skill_data["level"] = "intermediate"
        elif any(word in content for word in ["초급", "배우는", "공부"]):
            skill_data["level"] = "beginner"
        
        return skill_data
    
    def _extract_time_references(self, content: str) -> List[str]:
        """Extract time-related references"""
        time_patterns = [
            r'\d+년\s*전',
            r'\d+개월\s*전',
            r'\d+일\s*전',
            r'작년',
            r'올해',
            r'내년',
            r'예전에',
            r'최근에',
            r'\d{4}년'
        ]
        
        time_refs = []
        for pattern in time_patterns:
            matches = re.findall(pattern, content)
            time_refs.extend(matches)
        
        return time_refs
    
    def _create_identity_summary(self, identity_data: Dict) -> str:
        """Create identity summary"""
        attrs = identity_data.get("attributes", {})
        parts = []
        
        if "name" in attrs:
            parts.append(f"이름: {attrs['name']}")
        if "age" in attrs:
            parts.append(f"나이: {attrs['age']}")
        if "location" in attrs:
            parts.append(f"거주지: {attrs['location']}")
        
        return ", ".join(parts) if parts else "신원 정보"
    
    def _classify_fact_type(self, content: str) -> str:
        """Classify what type of fact this is"""
        if any(word in content for word in ["숫자", "통계", "데이터", "%"]):
            return "statistical"
        elif any(word in content for word in ["역사", "과거", "예전"]):
            return "historical"
        elif any(word in content for word in ["현재", "지금", "요즘"]):
            return "current"
        else:
            return "general"
    
    def _calculate_fact_importance(self, entities: List[Dict], keywords: List[str]) -> float:
        """Calculate importance score for facts"""
        base = 6.0
        
        # More entities = more important
        base += min(len(entities) * 0.5, 2.0)
        
        # More keywords = more important
        base += min(len(keywords) * 0.2, 1.0)
        
        return min(base, 9.0)
    
    def _calculate_experience_importance(self, content: str, time_refs: List[str]) -> float:
        """Calculate importance score for experiences"""
        base = 7.0
        
        # Recent experiences are more important
        if any(ref in time_refs for ref in ["최근", "올해", "이번"]):
            base += 1.0
        
        # Longer experiences might be more significant
        word_count = len(content.split())
        if word_count > 50:
            base += 0.5
        
        return min(base, 9.0)
    
    def _calculate_confidence(self, entities: List[Dict]) -> float:
        """Calculate overall confidence score"""
        if not entities:
            return 0.5
        
        # Average confidence of all entities
        total_conf = sum(e.get("confidence", 0.5) for e in entities)
        return total_conf / len(entities)