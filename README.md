# SSE Version - MCP with Server-Sent Events

This directory contains the SSE (Server-Sent Events) implementation of the MCP architecture.

## Directory Structure

```
sse/
├── mcp-rag/          # RAG orchestration service
├── mcp-db/           # Database service with pgvector
├── mcp-model/        # Model inference service
├── docker/           # Docker compose configurations
└── client/           # SSE client implementations
```

## Components

### 1. mcp-rag (Port 8093)
RAG orchestration service that coordinates between model and database services.

**Key Files:**
- `server.py` - SSE server implementation
- `src/clients/` - Contains multiple client implementations:
  - `base_client_old.py` - Original implementation (has issues)
  - `base_client.py` - Minimal implementation (creates fresh connections)
  - `base_client_fixed.py` - Enhanced with retry logic and health checks
- `tools/` - RAG tools:
  - `tool_rag_orchestrator.py` - Current implementation
  - `tool_rag_orchestrator_backup.py` - Original version
  - `tool_rag_orchestrator_fixed.py` - Version with fixes
  - `tool_rag_orchestrator_sse.py` - SSE-specific implementation

### 2. mcp-db (Port 8092)
PostgreSQL with pgvector for vector storage.

**Key Files:**
- `server.py` - SSE server for database operations
- `tools/tool_db_core.py` - Database operations (store, search, batch operations)
- `init.sql` - Database initialization script

### 3. mcp-model (Port 8091)
Model inference service for embeddings and LLM.

**Key Files:**
- `server.py` - SSE server for model inference
- `tools/tool_model.py` - Model inference operations

## Running SSE Version

### Basic Setup (Original)
```bash
cd docker
docker-compose -f docker-compose.yml up -d
```

### 3-Layer Architecture (Recommended)
```bash
cd docker
docker-compose -f docker-compose-3layer.yml up -d
```

### Development Mode
```bash
cd docker
docker-compose -f docker-compose-dev-3layer.yml up -d
```

## Client Usage

### Basic SSE Client
```bash
cd client
python client-rag.py --action save --content "Test document"
python client-rag.py --action search --query "test"
```

### Reliable SSE Client (with retry logic)
```bash
python client-rag-reliable.py --action save --content "Test document"
```

## Known Issues in Original SSE

1. **ClosedResourceError**: SSE connections being reused after closure
2. **Async Task Cancellation**: Context management issues
3. **Connection Timeouts**: No automatic reconnection
4. **Global Client Instances**: Causes connection reuse problems

## Fixes Applied in Enhanced Versions

1. **base_client_fixed.py**:
   - Connection health checks
   - Automatic reconnection
   - Retry logic with exponential backoff
   - Connection locking

2. **Endpoint Mounting Fix**:
   ```python
   # Fixed trailing slash issue
   Mount("/messages/", app=sse.handle_post_message)
   ```

3. **Per-Request Connections**:
   - Creates fresh connection for each tool call
   - Properly closes connections after use

## Environment Variables

```env
# Model service
MODEL_MCP_URL=http://mcp-model:8091/sse

# Database service
DB_MCP_URL=http://mcp-db:8092/sse

# Database credentials
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=vector_db

# Model settings
EMBEDDING_MODEL=bge-m3
LLM_MODEL=EXAONE-3.5-2.4B-Instruct
```

## Troubleshooting

### Connection Issues
1. Check service logs: `docker logs mcp-rag`
2. Verify endpoints have trailing slashes
3. Ensure services are healthy: `docker ps`

### Database Issues
1. Check vector dimensions (1024 for BGE-M3)
2. Verify pgvector extension is installed
3. Check connection pool status

### Performance Issues
1. Use `base_client.py` for better stability
2. Consider switching to HTTP version for production
3. Monitor connection pool usage