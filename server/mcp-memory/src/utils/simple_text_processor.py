"""
Simple Text Processor - No complex imports
Provides basic text processing without dependency issues
"""

import re
from typing import Dict, List, Any, Optional

class SimpleTextProcessor:
    """Simple text processor that works without complex imports"""
    
    @staticmethod
    def extract_korean_name(text: str) -> Optional[str]:
        """Extract Korean name from text"""
        name_patterns = [
            r"저는\s+([가-힣]{2,4})이고",
            r"저는\s+([가-힣]{2,4})입니다", 
            r"제\s+이름은\s+([가-힣]{2,4})",
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, text)
            if match:
                name = match.group(1)
                if 2 <= len(name) <= 4 and name not in ["그것", "이것", "저것"]:
                    return name
        return None
    
    @staticmethod
    def extract_technologies(text: str) -> List[str]:
        """Extract technology mentions"""
        tech_keywords = [
            "python", "파이썬", "java", "자바", "javascript", "자바스크립트",
            "react", "리액트", "fastapi", "django", "장고", "docker", "도커",
            "kubernetes", "쿠버네티스", "postgresql", "mongodb"
        ]
        
        found_tech = []
        text_lower = text.lower()
        
        for tech in tech_keywords:
            if tech in text_lower:
                found_tech.append(tech)
        
        return found_tech
    
    @staticmethod
    def extract_hobbies(text: str) -> List[str]:
        """Extract hobby mentions"""
        hobby_keywords = [
            "등산", "독서", "여행", "음악", "운동", "게임", "요리", "영화", "사진"
        ]
        
        found_hobbies = []
        text_lower = text.lower()
        
        for hobby in hobby_keywords:
            if hobby in text_lower:
                found_hobbies.append(hobby)
        
        return found_hobbies
    
    @staticmethod
    def extract_job_titles(text: str) -> List[str]:
        """Extract job title mentions"""
        job_keywords = [
            "developer", "개발자", "engineer", "엔지니어", "manager", "매니저",
            "cto", "ceo", "lead", "리드"
        ]
        
        found_jobs = []
        text_lower = text.lower()
        
        for job in job_keywords:
            if job in text_lower:
                found_jobs.append(job)
        
        return found_jobs