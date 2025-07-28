#!/usr/bin/env python3
"""
Script to fix database dimensions for BGE-M3 embeddings
This recreates tables with the correct 1024 dimensions
"""

import asyncio
import asyncpg
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def fix_database_dimensions():
    """Fix the database to use 1024 dimensions for BGE-M3"""
    
    # Database connection
    conn_string = "postgresql://postgres:password@localhost:5432/vector_db"
    
    try:
        # Connect to database
        conn = await asyncpg.connect(conn_string)
        logger.info("Connected to database")
        
        # Step 1: Create a backup of existing data (without embeddings for now)
        logger.info("Backing up existing memories...")
        backup_data = await conn.fetch("""
            SELECT id, content, metadata, created_at, updated_at
            FROM memories
        """)
        logger.info(f"Backed up {len(backup_data)} memories")
        
        # Step 2: Drop the old table
        logger.info("Dropping old memories table...")
        await conn.execute("DROP TABLE IF EXISTS memories CASCADE")
        
        # Step 3: Create new table with 1024 dimensions
        logger.info("Creating new memories table with 1024 dimensions...")
        await conn.execute("""
            CREATE TABLE memories (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                embedding vector(1024),
                metadata JSONB DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Step 4: Create indexes
        logger.info("Creating indexes...")
        await conn.execute("""
            CREATE INDEX idx_memories_embedding ON memories 
            USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)
        """)
        await conn.execute("CREATE INDEX idx_memories_metadata ON memories USING gin (metadata)")
        await conn.execute("CREATE INDEX idx_memories_created_at ON memories (created_at DESC)")
        
        # Step 5: Create trigger for updated_at
        await conn.execute("""
            CREATE OR REPLACE FUNCTION update_updated_at_column()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = CURRENT_TIMESTAMP;
                RETURN NEW;
            END;
            $$ language 'plpgsql';
        """)
        
        await conn.execute("""
            CREATE TRIGGER update_memories_updated_at 
            BEFORE UPDATE ON memories 
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()
        """)
        
        # Step 6: Restore data (without embeddings - they'll be regenerated)
        if backup_data:
            logger.info("Restoring backed up data...")
            for row in backup_data:
                await conn.execute("""
                    INSERT INTO memories (id, content, metadata, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, $5)
                """, row['id'], row['content'], row['metadata'], row['created_at'], row['updated_at'])
            logger.info(f"Restored {len(backup_data)} memories")
        
        # Step 7: Create user_memories table with correct dimensions
        logger.info("Creating user_memories table...")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS user_memories (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                session_id TEXT,
                memory_type TEXT,
                content TEXT NOT NULL,
                embedding vector(1024),
                metadata JSONB DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes for user_memories
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_memories_user_id ON user_memories (user_id)
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_memories_session_id ON user_memories (session_id)
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_memories_type ON user_memories (memory_type)
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_memories_embedding ON user_memories 
            USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)
        """)
        
        # Create trigger for user_memories
        await conn.execute("""
            CREATE TRIGGER update_user_memories_updated_at 
            BEFORE UPDATE ON user_memories 
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()
        """)
        
        logger.info("Database fixed successfully!")
        
        # Show current tables
        tables = await conn.fetch("""
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public'
        """)
        logger.info("Current tables:")
        for table in tables:
            logger.info(f"  - {table['tablename']}")
        
        await conn.close()
        
    except Exception as e:
        logger.error(f"Error fixing database: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(fix_database_dimensions())