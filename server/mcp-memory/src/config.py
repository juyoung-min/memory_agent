"""
Configuration Management for Memory Agent System
Handles all configuration settings, environment variables, and system parameters
"""
# config.py
import os
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

class AgentType(Enum):
    """Supported agent types"""
    BASIC = "basic"
    REACT = "react"
    HYBRID = "hybrid"

class StorageBackend(Enum):
    """Supported storage backends"""
    MEMORY = "memory"
    POSTGRESQL = "postgresql"
    SQLITE = "sqlite"

@dataclass
class AgentConfig:
    """Configuration for memory agents"""
    agent_type: AgentType = AgentType.REACT
    enable_intelligence: bool = True
    max_reasoning_steps: int = 8
    importance_threshold: float = 6.0
    context_window_size: int = 10
    enable_detailed_logging: bool = True
    tool_orchestration_strategy: str = "comprehensive"

@dataclass
class StorageConfig:
    """Configuration for storage backends"""
    backend_type: StorageBackend = StorageBackend.MEMORY
    connection_string: Optional[str] = None
    max_connections: int = 10
    connection_timeout: int = 30
    enable_connection_pooling: bool = True

@dataclass
class IntelligenceConfig:
    """Configuration for intelligence layer"""
    enable_entity_extraction: bool = True
    enable_sentiment_analysis: bool = True
    enable_topic_classification: bool = True
    enable_importance_calculation: bool = True
    language_models: Dict[str, str] = None

class Config:
    """
    Central configuration management for the memory agent system
    Handles environment variables, default settings, and configuration validation
    """
    
    def __init__(self, config_file: Optional[str] = None, env_prefix: str = "MEMORY_AGENT"):
        self.env_prefix = env_prefix
        self.config_file = config_file
        
        # Initialize configurations
        self.agent = self._load_agent_config()
        self.storage = self._load_storage_config()
        self.intelligence = self._load_intelligence_config()
        
        # System settings
        self.system = self._load_system_config()
    
    def _load_agent_config(self) -> AgentConfig:
        """Load agent configuration from environment or defaults"""
        return AgentConfig(
            agent_type=AgentType(self._get_env("AGENT_TYPE", AgentType.REACT.value)),
            enable_intelligence=self._get_env_bool("ENABLE_INTELLIGENCE", True),
            max_reasoning_steps=self._get_env_int("MAX_REASONING_STEPS", 8),
            importance_threshold=self._get_env_float("IMPORTANCE_THRESHOLD", 6.0),
            context_window_size=self._get_env_int("CONTEXT_WINDOW_SIZE", 10),
            enable_detailed_logging=self._get_env_bool("ENABLE_DETAILED_LOGGING", True),
            tool_orchestration_strategy=self._get_env("TOOL_ORCHESTRATION_STRATEGY", "comprehensive")
        )
    
    def _load_storage_config(self) -> StorageConfig:
        """Load storage configuration from environment or defaults"""
        return StorageConfig(
            backend_type=StorageBackend(self._get_env("STORAGE_BACKEND", StorageBackend.MEMORY.value)),
            connection_string=self._get_env("STORAGE_CONNECTION_STRING", None),
            max_connections=self._get_env_int("STORAGE_MAX_CONNECTIONS", 10),
            connection_timeout=self._get_env_int("STORAGE_CONNECTION_TIMEOUT", 30),
            enable_connection_pooling=self._get_env_bool("STORAGE_ENABLE_POOLING", True)
        )
    
    def _load_intelligence_config(self) -> IntelligenceConfig:
        """Load intelligence configuration from environment or defaults"""
        default_models = {
            "classification": "local",
            "extraction": "local", 
            "sentiment": "local"
        }
        
        return IntelligenceConfig(
            enable_entity_extraction=self._get_env_bool("ENABLE_ENTITY_EXTRACTION", True),
            enable_sentiment_analysis=self._get_env_bool("ENABLE_SENTIMENT_ANALYSIS", True),
            enable_topic_classification=self._get_env_bool("ENABLE_TOPIC_CLASSIFICATION", True),
            enable_importance_calculation=self._get_env_bool("ENABLE_IMPORTANCE_CALCULATION", True),
            language_models=self._get_env_dict("LANGUAGE_MODELS", default_models)
        )
    
    def _load_system_config(self) -> Dict[str, Any]:
        """Load system-wide configuration"""
        return {
            "debug_mode": self._get_env_bool("DEBUG_MODE", False),
            "log_level": self._get_env("LOG_LEVEL", "INFO"),
            "max_memory_usage_mb": self._get_env_int("MAX_MEMORY_USAGE_MB", 1024),
            "enable_metrics": self._get_env_bool("ENABLE_METRICS", True),
            "metrics_port": self._get_env_int("METRICS_PORT", 8080),
            "health_check_interval": self._get_env_int("HEALTH_CHECK_INTERVAL", 60),
            "session_timeout": self._get_env_int("SESSION_TIMEOUT", 3600),
            "max_sessions_per_user": self._get_env_int("MAX_SESSIONS_PER_USER", 10)
        }
    
    def _get_env(self, key: str, default: Any = None) -> str:
        """Get environment variable with prefix"""
        return os.getenv(f"{self.env_prefix}_{key}", default)
    
    def _get_env_bool(self, key: str, default: bool = False) -> bool:
        """Get boolean environment variable"""
        value = self._get_env(key, str(default).lower())
        return value.lower() in ("true", "1", "yes", "on")
    
    def _get_env_int(self, key: str, default: int = 0) -> int:
        """Get integer environment variable"""
        try:
            return int(self._get_env(key, str(default)))
        except (ValueError, TypeError):
            return default
    
    def _get_env_float(self, key: str, default: float = 0.0) -> float:
        """Get float environment variable"""
        try:
            return float(self._get_env(key, str(default)))
        except (ValueError, TypeError):
            return default
    
    def _get_env_dict(self, key: str, default: Dict[str, Any] = None) -> Dict[str, Any]:
        """Get dictionary environment variable (JSON format)"""
        import json
        if default is None:
            default = {}
        
        value = self._get_env(key)
        if not value:
            return default
        
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return default
    
    def validate(self) -> Dict[str, Any]:
        """
        Validate configuration and return validation results
        """
        validation_results = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        # Validate agent configuration
        if self.agent.importance_threshold < 0 or self.agent.importance_threshold > 10:
            validation_results["errors"].append("importance_threshold must be between 0 and 10")
            validation_results["valid"] = False
        
        if self.agent.max_reasoning_steps < 1 or self.agent.max_reasoning_steps > 20:
            validation_results["warnings"].append("max_reasoning_steps should be between 1 and 20")
        
        # Validate storage configuration
        if self.storage.backend_type == StorageBackend.POSTGRESQL and not self.storage.connection_string:
            validation_results["errors"].append("PostgreSQL backend requires connection_string")
            validation_results["valid"] = False
        
        if self.storage.max_connections < 1:
            validation_results["errors"].append("max_connections must be at least 1")
            validation_results["valid"] = False
        
        # Validate system configuration
        max_memory = self.system.get("max_memory_usage_mb", 1024)
        if max_memory < 256:
            validation_results["warnings"].append("max_memory_usage_mb below 256MB may cause performance issues")
        
        return validation_results
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            "agent": {
                "agent_type": self.agent.agent_type.value,
                "enable_intelligence": self.agent.enable_intelligence,
                "max_reasoning_steps": self.agent.max_reasoning_steps,
                "importance_threshold": self.agent.importance_threshold,
                "context_window_size": self.agent.context_window_size,
                "enable_detailed_logging": self.agent.enable_detailed_logging,
                "tool_orchestration_strategy": self.agent.tool_orchestration_strategy
            },
            "storage": {
                "backend_type": self.storage.backend_type.value,
                "max_connections": self.storage.max_connections,
                "connection_timeout": self.storage.connection_timeout,
                "enable_connection_pooling": self.storage.enable_connection_pooling
            },
            "intelligence": {
                "enable_entity_extraction": self.intelligence.enable_entity_extraction,
                "enable_sentiment_analysis": self.intelligence.enable_sentiment_analysis,
                "enable_topic_classification": self.intelligence.enable_topic_classification,
                "enable_importance_calculation": self.intelligence.enable_importance_calculation,
                "language_models": self.intelligence.language_models
            },
            "system": self.system
        }
    
    @classmethod
    def create_development_config(cls) -> 'Config':
        """Create configuration optimized for development"""
        config = cls()
        config.agent.enable_detailed_logging = True
        config.system["debug_mode"] = True
        config.system["log_level"] = "DEBUG"
        return config
    
    @classmethod 
    def create_production_config(cls) -> 'Config':
        """Create configuration optimized for production"""
        config = cls()
        config.agent.enable_detailed_logging = False
        config.system["debug_mode"] = False
        config.system["log_level"] = "INFO"
        config.storage.enable_connection_pooling = True
        return config
    
    def update_from_dict(self, config_dict: Dict[str, Any]):
        """Update configuration from dictionary"""
        if "agent" in config_dict:
            agent_config = config_dict["agent"]
            for key, value in agent_config.items():
                if hasattr(self.agent, key):
                    if key == "agent_type":
                        setattr(self.agent, key, AgentType(value))
                    else:
                        setattr(self.agent, key, value)
        
        if "storage" in config_dict:
            storage_config = config_dict["storage"]
            for key, value in storage_config.items():
                if hasattr(self.storage, key):
                    if key == "backend_type":
                        setattr(self.storage, key, StorageBackend(value))
                    else:
                        setattr(self.storage, key, value)
        
        if "intelligence" in config_dict:
            intelligence_config = config_dict["intelligence"]
            for key, value in intelligence_config.items():
                if hasattr(self.intelligence, key):
                    setattr(self.intelligence, key, value)
        
        if "system" in config_dict:
            self.system.update(config_dict["system"])

# Global configuration instance
default_config = Config()

def get_config() -> Config:
    """Get the global configuration instance"""
    return default_config

def set_config(config: Config):
    """Set the global configuration instance"""
    global default_config
    default_config = config