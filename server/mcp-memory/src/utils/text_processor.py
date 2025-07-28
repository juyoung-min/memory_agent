"""
General Text Processing Module
Configurable, extensible text processing that's not hardcoded
"""

import re
import json
import yaml
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass
from pathlib import Path

@dataclass
class ExtractionPattern:
    """Configuration for text extraction patterns"""
    name: str
    patterns: List[str]
    pattern_type: str  # 'regex', 'keyword', 'fuzzy'
    case_sensitive: bool = False
    confidence_threshold: float = 0.7

@dataclass
class EntityConfig:
    """Configuration for entity extraction"""
    entity_type: str
    patterns: List[ExtractionPattern]
    validation_rules: Optional[Dict[str, Any]] = None
    post_processing: Optional[List[str]] = None

class ConfigurableTextProcessor:
    """
    General text processor that works with configuration files
    Not hardcoded - everything is configurable
    """
    
    def __init__(self, config_path: Optional[str] = None, language: str = "auto"):
        """
        Initialize with configuration file or defaults
        
        Args:
            config_path: Path to configuration file (JSON/YAML)
            language: Language code or 'auto' for detection
        """
        self.language = language
        self.config = {}
        self.entity_configs = {}
        
        # Load configuration
        if config_path and Path(config_path).exists():
            self.load_config(config_path)
        else:
            self._load_default_config()
    
    def load_config(self, config_path: str):
        """Load configuration from file"""
        path = Path(config_path)
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                if path.suffix.lower() in ['.yaml', '.yml']:
                    self.config = yaml.safe_load(f)
                else:
                    self.config = json.load(f)
            
            self._parse_entity_configs()
            
        except Exception as e:
            print(f"Warning: Failed to load config {config_path}: {e}")
            self._load_default_config()
    
    def _load_default_config(self):
        """Load minimal default configuration"""
        self.config = {
            "entities": {
                "person_name": {
                    "patterns": [
                        {
                            "name": "name_intro_pattern",
                            "patterns": [r"(?:I am|My name is|I'm|저는|제 이름은)\s+([A-Za-z가-힣\s]+)"],
                            "pattern_type": "regex",
                            "case_sensitive": False
                        }
                    ],
                    "validation_rules": {
                        "min_length": 2,
                        "max_length": 50,
                        "exclude_words": ["that", "this", "것", "이것", "그것"]
                    }
                },
                "technology": {
                    "patterns": [
                        {
                            "name": "tech_keywords",
                            "patterns": ["python", "java", "javascript", "react", "docker", "파이썬", "자바"],
                            "pattern_type": "keyword",
                            "case_sensitive": False
                        }
                    ]
                },
                "job_title": {
                    "patterns": [
                        {
                            "name": "job_keywords", 
                            "patterns": ["developer", "engineer", "manager", "개발자", "엔지니어", "매니저"],
                            "pattern_type": "keyword",
                            "case_sensitive": False
                        }
                    ]
                }
            },
            "preprocessing": {
                "normalize_whitespace": True,
                "remove_special_chars": False,
                "lowercase_for_matching": True
            },
            "language_specific": {
                "korean": {
                    "particle_removal": ["이고", "입니다", "이에요", "예요"],
                    "honorific_detection": True
                }
            }
        }
        
        self._parse_entity_configs()
    
    def _parse_entity_configs(self):
        """Parse configuration into EntityConfig objects"""
        self.entity_configs = {}
        
        for entity_type, config in self.config.get("entities", {}).items():
            patterns = []
            
            for pattern_config in config.get("patterns", []):
                pattern = ExtractionPattern(
                    name=pattern_config["name"],
                    patterns=pattern_config["patterns"],
                    pattern_type=pattern_config["pattern_type"],
                    case_sensitive=pattern_config.get("case_sensitive", False),
                    confidence_threshold=pattern_config.get("confidence_threshold", 0.7)
                )
                patterns.append(pattern)
            
            entity_config = EntityConfig(
                entity_type=entity_type,
                patterns=patterns,
                validation_rules=config.get("validation_rules"),
                post_processing=config.get("post_processing")
            )
            
            self.entity_configs[entity_type] = entity_config
    
    def extract_entities(self, text: str, entity_types: Optional[List[str]] = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        Extract entities from text using configured patterns
        
        Args:
            text: Input text
            entity_types: Specific entity types to extract (None for all)
            
        Returns:
            Dictionary of {entity_type: [extracted_entities]}
        """
        if entity_types is None:
            entity_types = list(self.entity_configs.keys())
        
        results = {}
        preprocessed_text = self._preprocess_text(text)
        
        for entity_type in entity_types:
            if entity_type not in self.entity_configs:
                continue
            
            entity_config = self.entity_configs[entity_type]
            extracted = self._extract_entity_type(preprocessed_text, entity_config)
            
            if extracted:
                results[entity_type] = extracted
        
        return results
    
    def _extract_entity_type(self, text: str, entity_config: EntityConfig) -> List[Dict[str, Any]]:
        """Extract specific entity type from text"""
        found_entities = []
        
        for pattern in entity_config.patterns:
            entities = self._apply_extraction_pattern(text, pattern)
            
            for entity in entities:
                # Validate entity
                if self._validate_entity(entity["value"], entity_config.validation_rules):
                    # Post-process entity
                    processed_value = self._post_process_entity(
                        entity["value"], 
                        entity_config.post_processing
                    )
                    
                    found_entities.append({
                        "value": processed_value,
                        "confidence": entity["confidence"],
                        "pattern_used": pattern.name,
                        "position": entity.get("position"),
                        "original_value": entity["value"]
                    })
        
        # Remove duplicates and sort by confidence
        unique_entities = self._deduplicate_entities(found_entities)
        return sorted(unique_entities, key=lambda x: x["confidence"], reverse=True)
    
    def _apply_extraction_pattern(self, text: str, pattern: ExtractionPattern) -> List[Dict[str, Any]]:
        """Apply a specific extraction pattern to text"""
        entities = []
        
        if pattern.pattern_type == "regex":
            entities.extend(self._extract_regex(text, pattern))
        elif pattern.pattern_type == "keyword":
            entities.extend(self._extract_keywords(text, pattern))
        elif pattern.pattern_type == "fuzzy":
            entities.extend(self._extract_fuzzy(text, pattern))
        
        return entities
    
    def _extract_regex(self, text: str, pattern: ExtractionPattern) -> List[Dict[str, Any]]:
        """Extract using regex patterns"""
        entities = []
        
        for regex_pattern in pattern.patterns:
            flags = 0 if pattern.case_sensitive else re.IGNORECASE
            
            try:
                matches = re.finditer(regex_pattern, text, flags)
                
                for match in matches:
                    # Get the captured group or full match
                    value = match.group(1) if match.groups() else match.group(0)
                    
                    entities.append({
                        "value": value.strip(),
                        "confidence": 0.9,  # High confidence for regex matches
                        "position": (match.start(), match.end())
                    })
                    
            except re.error as e:
                print(f"Warning: Invalid regex pattern '{regex_pattern}': {e}")
        
        return entities
    
    def _extract_keywords(self, text: str, pattern: ExtractionPattern) -> List[Dict[str, Any]]:
        """Extract using keyword matching"""
        entities = []
        text_for_matching = text.lower() if not pattern.case_sensitive else text
        
        for keyword in pattern.patterns:
            keyword_for_matching = keyword.lower() if not pattern.case_sensitive else keyword
            
            if keyword_for_matching in text_for_matching:
                # Find all positions
                start = 0
                while True:
                    pos = text_for_matching.find(keyword_for_matching, start)
                    if pos == -1:
                        break
                    
                    entities.append({
                        "value": text[pos:pos+len(keyword)],  # Preserve original case
                        "confidence": 0.8,  # Good confidence for keyword matches
                        "position": (pos, pos + len(keyword))
                    })
                    
                    start = pos + 1
        
        return entities
    
    def _extract_fuzzy(self, text: str, pattern: ExtractionPattern) -> List[Dict[str, Any]]:
        """Extract using fuzzy matching (requires additional libraries)"""
        # Placeholder for fuzzy matching
        # Could implement using libraries like fuzzywuzzy, rapidfuzz, etc.
        entities = []
        
        try:
            from fuzzywuzzy import fuzz
            
            words = text.split()
            
            for keyword in pattern.patterns:
                for i, word in enumerate(words):
                    ratio = fuzz.ratio(keyword.lower(), word.lower())
                    
                    if ratio >= pattern.confidence_threshold * 100:
                        entities.append({
                            "value": word,
                            "confidence": ratio / 100.0,
                            "position": None  # Could calculate if needed
                        })
                        
        except ImportError:
            # Fallback to keyword matching if fuzzy library not available
            return self._extract_keywords(text, pattern)
        
        return entities
    
    def _validate_entity(self, value: str, validation_rules: Optional[Dict[str, Any]]) -> bool:
        """Validate extracted entity against rules"""
        if not validation_rules:
            return True
        
        # Length validation
        if "min_length" in validation_rules:
            if len(value) < validation_rules["min_length"]:
                return False
        
        if "max_length" in validation_rules:
            if len(value) > validation_rules["max_length"]:
                return False
        
        # Exclude words
        if "exclude_words" in validation_rules:
            exclude_words = validation_rules["exclude_words"]
            if value.lower() in [word.lower() for word in exclude_words]:
                return False
        
        # Custom validation patterns
        if "must_match" in validation_rules:
            pattern = validation_rules["must_match"]
            if not re.search(pattern, value):
                return False
        
        if "must_not_match" in validation_rules:
            pattern = validation_rules["must_not_match"]
            if re.search(pattern, value):
                return False
        
        return True
    
    def _post_process_entity(self, value: str, post_processing: Optional[List[str]]) -> str:
        """Apply post-processing rules to entity"""
        if not post_processing:
            return value
        
        processed_value = value
        
        for rule in post_processing:
            if rule == "trim":
                processed_value = processed_value.strip()
            elif rule == "title_case":
                processed_value = processed_value.title()
            elif rule == "remove_particles":
                # Language-specific processing
                if self.language == "korean" or "korean" in self.config.get("language_specific", {}):
                    particles = self.config["language_specific"]["korean"]["particle_removal"]
                    for particle in particles:
                        processed_value = processed_value.replace(particle, "")
            elif rule.startswith("regex_replace:"):
                # Format: "regex_replace:pattern:replacement"
                parts = rule.split(":", 2)
                if len(parts) == 3:
                    pattern, replacement = parts[1], parts[2]
                    processed_value = re.sub(pattern, replacement, processed_value)
        
        return processed_value.strip()
    
    def _deduplicate_entities(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate entities"""
        seen_values = set()
        unique_entities = []
        
        for entity in entities:
            value_key = entity["value"].lower()
            
            if value_key not in seen_values:
                seen_values.add(value_key)
                unique_entities.append(entity)
        
        return unique_entities
    
    def _preprocess_text(self, text: str) -> str:
        """Preprocess text according to configuration"""
        processed = text
        
        preprocessing = self.config.get("preprocessing", {})
        
        if preprocessing.get("normalize_whitespace", True):
            processed = re.sub(r'\s+', ' ', processed.strip())
        
        if preprocessing.get("remove_special_chars", False):
            processed = re.sub(r'[^\w\s]', '', processed)
        
        return processed
    
    def add_entity_type(self, entity_type: str, patterns: List[Dict[str, Any]], 
                       validation_rules: Optional[Dict[str, Any]] = None):
        """Add new entity type dynamically"""
        pattern_objects = []
        
        for pattern_config in patterns:
            pattern = ExtractionPattern(
                name=pattern_config["name"],
                patterns=pattern_config["patterns"],
                pattern_type=pattern_config["pattern_type"],
                case_sensitive=pattern_config.get("case_sensitive", False),
                confidence_threshold=pattern_config.get("confidence_threshold", 0.7)
            )
            pattern_objects.append(pattern)
        
        entity_config = EntityConfig(
            entity_type=entity_type,
            patterns=pattern_objects,
            validation_rules=validation_rules
        )
        
        self.entity_configs[entity_type] = entity_config
    
    def save_config(self, file_path: str):
        """Save current configuration to file"""
        with open(file_path, 'w', encoding='utf-8') as f:
            if file_path.endswith('.yaml') or file_path.endswith('.yml'):
                yaml.dump(self.config, f, default_flow_style=False, allow_unicode=True)
            else:
                json.dump(self.config, f, indent=2, ensure_ascii=False)

# Factory function for backward compatibility
def create_text_processor(config_path: Optional[str] = None, language: str = "auto") -> ConfigurableTextProcessor:
    """Create a text processor instance"""
    return ConfigurableTextProcessor(config_path, language)

# Legacy TextProcessor for backward compatibility
class TextProcessor:
    """Legacy wrapper for backward compatibility"""
    
    def __init__(self):
        self.processor = ConfigurableTextProcessor()
    
    @staticmethod
    def extract_korean_name(text: str) -> Optional[str]:
        processor = ConfigurableTextProcessor()
        results = processor.extract_entities(text, ["person_name"])
        
        if "person_name" in results and results["person_name"]:
            return results["person_name"][0]["value"]
        return None
    
    @staticmethod
    def extract_technologies(text: str) -> List[str]:
        processor = ConfigurableTextProcessor()
        results = processor.extract_entities(text, ["technology"])
        
        if "technology" in results:
            return [entity["value"] for entity in results["technology"]]
        return []
    
    @staticmethod
    def extract_job_titles(text: str) -> List[str]:
        processor = ConfigurableTextProcessor()
        results = processor.extract_entities(text, ["job_title"])
        
        if "job_title" in results:
            return [entity["value"] for entity in results["job_title"]]
        return []