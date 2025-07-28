import os
import asyncpg
import logging
from contextlib import asynccontextmanager
from typing import Optional

logger = logging.getLogger(__name__)

# Connection pool
_db_pool: Optional[asyncpg.Pool] = None

async def create_pool():
    """Create database connection pool"""
    global _db_pool
    
    if _db_pool is None:
        # Database configuration from environment
        db_config = {
            "host": os.getenv("DB_HOST", "localhost"),
            "port": int(os.getenv("DB_PORT", "5432")),
            "database": os.getenv("DB_NAME", "vector_db"),
            "user": os.getenv("DB_USER", "postgres"),
            "password": os.getenv("DB_PASSWORD", "postgres"),
            "min_size": int(os.getenv("DB_MIN_CONNECTIONS", "5")),
            "max_size": int(os.getenv("DB_MAX_CONNECTIONS", "20")),
            "command_timeout": int(os.getenv("DB_COMMAND_TIMEOUT", "60")),
        }
        
        # SSL mode
        ssl_mode = os.getenv("DB_SSL_MODE", "prefer")
        if ssl_mode != "disable":
            db_config["ssl"] = ssl_mode
        
        logger.info(f"Creating database pool: {db_config['host']}:{db_config['port']}/{db_config['database']}")
        
        try:
            _db_pool = await asyncpg.create_pool(**db_config)
            logger.info("Database pool created successfully")
            
            # Test connection
            async with _db_pool.acquire() as conn:
                version = await conn.fetchval("SELECT version()")
                logger.info(f"Connected to: {version}")
                
                # Ensure pgvector extension
                await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
                
        except Exception as e:
            logger.error(f"Failed to create database pool: {e}")
            raise
    
    return _db_pool

async def close_pool():
    """Close database connection pool"""
    global _db_pool
    
    if _db_pool:
        await _db_pool.close()
        _db_pool = None
        logger.info("Database pool closed")

@asynccontextmanager
async def get_db_connection():
    """Get a database connection from the pool"""
    pool = await create_pool()
    
    async with pool.acquire() as connection:
        try:
            yield connection
        except Exception as e:
            logger.error(f"Database operation failed: {e}")
            raise

# Legacy compatibility
async def get_connection():
    """Get a database connection (legacy function)"""
    pool = await create_pool()
    return await pool.acquire()

async def release_connection(conn):
    """Release a database connection (legacy function)"""
    pool = await create_pool()
    await pool.release(conn)