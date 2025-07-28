import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class Config:
    """Configuration for RAG-MCP server"""
    
    # Server configuration
    host: str = os.getenv("RAG_HOST", "0.0.0.0")
    port: int = int(os.getenv("RAG_PORT", "8093"))
    
    # Service URLs
    model_mcp_url: str = os.getenv("MODEL_MCP_URL", "http://localhost:8091/sse")
    db_mcp_url: str = os.getenv("DB_MCP_URL", "http://localhost:8092/sse")
    
    # Default settings
    default_embedding_model: str = os.getenv("DEFAULT_EMBEDDING_MODEL", "bge-m3")
    default_llm_model: str = os.getenv("DEFAULT_LLM_MODEL", "EXAONE-3.5-2.4B-Instruct")
    default_collection: str = os.getenv("DEFAULT_COLLECTION", "memories")
    
    # Chunking settings
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "1000"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "200"))
    
    # Search settings
    default_search_limit: int = int(os.getenv("DEFAULT_SEARCH_LIMIT", "10"))
    default_similarity_threshold: float = float(os.getenv("DEFAULT_SIMILARITY_THRESHOLD", "0.5"))
    
    # Logging
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Timeouts
    model_timeout: int = int(os.getenv("MODEL_TIMEOUT", "60"))
    db_timeout: int = int(os.getenv("DB_TIMEOUT", "30"))

def get_config() -> Config:
    """Get configuration instance"""
    return Config()