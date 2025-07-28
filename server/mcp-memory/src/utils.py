"""
Utility Functions for Memory Agent System
Common utilities, helpers, and shared functionality
"""

import re
import json
import uuid
import hashlib
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass

@dataclass
class ValidationResult:
    """Result of validation operations"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]

# Import simple text processor to avoid complex dependencies
try:
    from .simple_text_processor import SimpleTextProcessor
    _processor = SimpleTextProcessor()
except ImportError:
    # Fallback 
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), 'utils'))
    from simple_text_processor import SimpleTextProcessor
    _processor = SimpleTextProcessor()

class TextProcessor:
    """
    Text Processor - Backward compatible with simple implementation
    """
    
    @staticmethod
    def extract_korean_name(text: str) -> Optional[str]:
        """Extract Korean name"""
        return _processor.extract_korean_name(text)
    
    @staticmethod
    def extract_technologies(text: str) -> List[str]:
        """Extract technologies"""
        return _processor.extract_technologies(text)
    
    @staticmethod
    def extract_hobbies(text: str) -> List[str]:
        """Extract hobbies"""
        return _processor.extract_hobbies(text)
    
    @staticmethod
    def extract_job_titles(text: str) -> List[str]:
        """Extract job titles"""
        return _processor.extract_job_titles(text)

class MessageAnalyzer:
    """Analyze messages for various characteristics"""
    
    @staticmethod
    def calculate_complexity(text: str) -> Dict[str, Any]:
        """Calculate message complexity metrics"""
        words = text.split()
        sentences = re.split(r'[.!?]', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        # Character analysis
        korean_chars = len(re.findall(r'[가-힣]', text))
        english_chars = len(re.findall(r'[a-zA-Z]', text))
        numbers = len(re.findall(r'\d', text))
        
        return {
            "word_count": len(words),
            "sentence_count": len(sentences),
            "avg_word_length": sum(len(word) for word in words) / len(words) if words else 0,
            "korean_ratio": korean_chars / len(text) if text else 0,
            "english_ratio": english_chars / len(text) if text else 0,
            "number_ratio": numbers / len(text) if text else 0,
            "complexity_score": MessageAnalyzer._calculate_complexity_score(words, sentences)
        }
    
    @staticmethod
    def _calculate_complexity_score(words: List[str], sentences: List[str]) -> float:
        """Calculate overall complexity score (0-10)"""
        if not words:
            return 0.0
        
        word_count = len(words)
        sentence_count = len(sentences)
        avg_words_per_sentence = word_count / sentence_count if sentence_count > 0 else word_count
        
        # Base score from word count
        score = min(5.0, word_count / 10.0)
        
        # Sentence complexity
        if avg_words_per_sentence > 15:
            score += 2.0
        elif avg_words_per_sentence > 10:
            score += 1.0
        
        # Technical terms boost
        technical_indicators = sum(1 for word in words if any(tech in word.lower() 
                                 for tech in ["개발", "프로그래밍", "시스템", "기술", "프로젝트"]))
        score += min(2.0, technical_indicators * 0.5)
        
        # Detailed information boost
        detail_indicators = sum(1 for word in words if any(detail in word.lower()
                               for detail in ["구체적", "자세히", "특히", "정확히"]))
        score += min(1.0, detail_indicators * 0.5)
        
        return min(10.0, score)
    
    @staticmethod
    def detect_intent(text: str) -> Dict[str, Any]:
        """Detect user intent from message"""
        text_lower = text.lower()
        
        intents = {
            "introduce": {
                "patterns": ["저는", "제가", "이름은", "소개"],
                "confidence": 0.0
            },
            "question": {
                "patterns": ["무엇", "어떻게", "왜", "언제", "어디서", "누구", "?"],
                "confidence": 0.0
            },
            "share_info": {
                "patterns": ["좋아해", "관심", "취미", "목표", "계획"],
                "confidence": 0.0
            },
            "request_help": {
                "patterns": ["도와", "알려", "가르쳐", "설명", "도움"],
                "confidence": 0.0
            },
            "casual_chat": {
                "patterns": ["안녕", "날씨", "오늘", "어떻게", "잘"],
                "confidence": 0.0
            }
        }
        
        # Calculate confidence for each intent
        for intent_name, intent_data in intents.items():
            patterns = intent_data["patterns"]
            matches = sum(1 for pattern in patterns if pattern in text_lower)
            intent_data["confidence"] = min(1.0, matches / len(patterns) * 2)
        
        # Find dominant intent
        dominant_intent = max(intents.items(), key=lambda x: x[1]["confidence"])
        
        return {
            "dominant_intent": dominant_intent[0],
            "confidence": dominant_intent[1]["confidence"],
            "all_intents": {name: data["confidence"] for name, data in intents.items()}
        }

class MemoryUtils:
    """Utilities for memory management"""
    
    @staticmethod
    def generate_memory_id() -> str:
        """Generate unique memory ID"""
        return str(uuid.uuid4())
    
    @staticmethod
    def calculate_memory_hash(content: str, user_id: str) -> str:
        """Calculate hash for deduplication"""
        combined = f"{user_id}:{content.strip().lower()}"
        return hashlib.md5(combined.encode()).hexdigest()
    
    @staticmethod
    def normalize_content(content: str) -> str:
        """Normalize content for consistent storage"""
        # Remove extra whitespace
        content = re.sub(r'\s+', ' ', content.strip())
        
        # Normalize punctuation
        content = re.sub(r'[!]{2,}', '!', content)
        content = re.sub(r'[?]{2,}', '?', content)
        content = re.sub(r'[.]{2,}', '...', content)
        
        return content
    
    @staticmethod
    def validate_memory_data(user_id: str, session_id: str, content: str, 
                           importance: float = None) -> ValidationResult:
        """Validate memory data before storage"""
        errors = []
        warnings = []
        
        # Validate user_id
        if not user_id or not user_id.strip():
            errors.append("user_id cannot be empty")
        elif len(user_id) > 100:
            errors.append("user_id too long (max 100 characters)")
        
        # Validate session_id
        if not session_id or not session_id.strip():
            errors.append("session_id cannot be empty")
        elif len(session_id) > 100:
            errors.append("session_id too long (max 100 characters)")
        
        # Validate content
        if not content or not content.strip():
            errors.append("content cannot be empty")
        elif len(content) > 10000:
            errors.append("content too long (max 10000 characters)")
        elif len(content.strip()) < 5:
            warnings.append("content very short (less than 5 characters)")
        
        # Validate importance
        if importance is not None:
            if not isinstance(importance, (int, float)):
                errors.append("importance must be a number")
            elif importance < 0 or importance > 10:
                errors.append("importance must be between 0 and 10")
            elif importance < 1:
                warnings.append("very low importance score")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

class DateTimeUtils:
    """Date and time utilities"""
    
    @staticmethod
    def utc_now() -> datetime:
        """Get current UTC datetime"""
        return datetime.now(timezone.utc)
    
    @staticmethod
    def format_datetime(dt: datetime) -> str:
        """Format datetime for display"""
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    
    @staticmethod
    def parse_datetime(dt_str: str) -> datetime:
        """Parse datetime string"""
        try:
            return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        except ValueError:
            return datetime.now(timezone.utc)
    
    @staticmethod
    def time_ago(dt: datetime) -> str:
        """Get human-readable time difference"""
        now = DateTimeUtils.utc_now()
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        
        diff = now - dt
        seconds = diff.total_seconds()
        
        if seconds < 60:
            return "방금 전"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            return f"{minutes}분 전"
        elif seconds < 86400:
            hours = int(seconds / 3600)
            return f"{hours}시간 전"
        else:
            days = int(seconds / 86400)
            return f"{days}일 전"

class ConfigUtils:
    """Configuration utilities"""
    
    @staticmethod
    def load_json_config(file_path: str) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError, IOError):
            return {}
    
    @staticmethod
    def save_json_config(config: Dict[str, Any], file_path: str) -> bool:
        """Save configuration to JSON file"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            return True
        except (IOError, TypeError):
            return False
    
    @staticmethod
    def merge_configs(base_config: Dict[str, Any], override_config: Dict[str, Any]) -> Dict[str, Any]:
        """Merge two configuration dictionaries"""
        result = base_config.copy()
        
        for key, value in override_config.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = ConfigUtils.merge_configs(result[key], value)
            else:
                result[key] = value
        
        return result

# Export main utility classes
__all__ = [
    'TextProcessor',
    'MessageAnalyzer', 
    'MemoryUtils',
    'DateTimeUtils',
    'ConfigUtils',
    'ValidationResult'
]