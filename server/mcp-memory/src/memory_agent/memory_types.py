# memory_types.py
"""Memory Types and Data Structures"""

from enum import Enum
from typing import Dict, Any, Optional
from datetime import datetime

class MemoryType(Enum):
    """Enhanced memory types supporting both basic and hierarchical classification"""
    FACT = "fact"
    PREFERENCE = "preference"
    IDENTITY = "identity"
    PROFESSION = "profession"
    SKILL = "skill"
    GOAL = "goal"
    HOBBY = "hobby"
    EXPERIENCE = "experience"
    CONTEXT = "context"
    CONVERSATION = "conversation"

class Memory:
    """Enhanced Memory class with all required attributes including session_id"""
    
    def __init__(self, user_id: str, session_id: str, type: MemoryType, content: str,
                 importance: float = 5.0, metadata: Dict[str, Any] = None):
        self.user_id = user_id
        self.session_id = session_id  # REQUIRED attribute
        self.type = type
        self.content = content
        self.importance = importance
        self.timestamp = datetime.now()
        self.metadata = metadata or {}
        self.id = f"{user_id}_{session_id}_{int(self.timestamp.timestamp())}_{hash(content) % 1000}"
    
    def get_content_safe(self) -> str:
        """Get content safely, handling None values"""
        return self.content if self.content else ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert memory to dictionary for serialization"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "type": self.type.value,
            "content": self.content,
            "importance": self.importance,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }
    
    def __str__(self) -> str:
        return f"Memory(id={self.id}, type={self.type.value}, content='{self.content[:50]}...')"