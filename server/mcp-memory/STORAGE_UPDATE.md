# Storage Update: All Memories in Database

## Summary of Changes

As requested, all memory types are now stored in the database (DB-MCP) instead of RAG-MCP. This ensures consistent storage and retrieval patterns across all memory types.

## Changes Made

### 1. Storage Strategy Updates (`src/storage_strategy.py`)

Updated storage strategies to use DB as primary storage:

- **Conversational**: 
  - Before: Primary=RAG, includes_rag=True
  - After: Primary=DB, includes_rag=False

- **Large Content (Experiences)**:
  - Before: includes_rag=True
  - After: includes_rag=False

### 2. Orchestrator Tool Updates

#### `tool_memory_orchestrator_sse.py`:
- Removed RAG storage logic from `process_message()`
- Removed RAG storage from `store_memory_by_type()`
- Updated `get_conversation_history()` to retrieve from DB instead of RAG

#### `tool_memory_orchestrator_enhanced.py`:
- Updated `get_conversation_history()` to use DB search
- RAG storage logic remains but won't execute (includes_rag=False)

### 3. All Memory Types Storage Location

| Memory Type | Storage | Embeddings | Search Method |
|-------------|---------|------------|---------------|
| conversation | DB | Yes | Semantic search in DB |
| experience | DB | Yes | Semantic search in DB |
| identity | DB | Yes | Semantic search in DB |
| preference | DB | Yes | Semantic search in DB |
| skill | DB | Yes | Semantic search in DB |
| fact | DB | Yes | Semantic search in DB |
| context | Cache/DB | Optional | Time-based |

## Benefits

1. **Consistency**: All memories follow the same storage pattern
2. **Simplicity**: No need to manage multiple storage backends
3. **Performance**: DB with pgvector provides efficient semantic search
4. **Cost**: Reduced complexity and storage costs

## Migration Notes

Existing memories stored in RAG-MCP will remain there but won't be accessible through the Memory Agent. If needed, a migration script can be created to move historical data from RAG-MCP to DB-MCP.

## Testing

To verify the changes:

```bash
# Test enhanced client
uv run python client-memory-enhanced.py

# Check that memories are stored in DB
# Look for log messages like:
# "Stored conversation memory in database"
# "Retrieving conversation history for user X from database"
```

## Future Considerations

1. **Search Optimization**: With all data in DB, we can optimize indexes
2. **Backup Strategy**: Implement regular DB backups
3. **Data Retention**: Add policies for old conversation cleanup
4. **Performance Monitoring**: Track query performance as data grows