-- Fix database dimensions for BGE-M3 (1024 dimensions)

-- Step 1: Backup existing data
CREATE TEMP TABLE memories_backup AS 
SELECT id, content, metadata, created_at, updated_at 
FROM memories;

-- Step 2: Drop old table
DROP TABLE IF EXISTS memories CASCADE;

-- Step 3: Create new table with 1024 dimensions
CREATE TABLE memories (
    id TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    embedding vector(1024),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Step 4: Create indexes
CREATE INDEX idx_memories_embedding ON memories 
USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_memories_metadata ON memories USING gin (metadata);
CREATE INDEX idx_memories_created_at ON memories (created_at DESC);

-- Step 5: Create/update trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Step 6: Create trigger
CREATE TRIGGER update_memories_updated_at 
BEFORE UPDATE ON memories 
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Step 7: Restore data
INSERT INTO memories (id, content, metadata, created_at, updated_at)
SELECT id, content, metadata, created_at, updated_at
FROM memories_backup;

-- Step 8: Create user_memories table
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
);

-- Step 9: Create indexes for user_memories
CREATE INDEX IF NOT EXISTS idx_user_memories_user_id ON user_memories (user_id);
CREATE INDEX IF NOT EXISTS idx_user_memories_session_id ON user_memories (session_id);
CREATE INDEX IF NOT EXISTS idx_user_memories_type ON user_memories (memory_type);
CREATE INDEX IF NOT EXISTS idx_user_memories_embedding ON user_memories 
USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Step 10: Create trigger for user_memories
DROP TRIGGER IF EXISTS update_user_memories_updated_at ON user_memories;
CREATE TRIGGER update_user_memories_updated_at 
BEFORE UPDATE ON user_memories 
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Show results
SELECT 'Fixed memories table to use 1024 dimensions' as status;
SELECT COUNT(*) as restored_count FROM memories;