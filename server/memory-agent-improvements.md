# Memory Agent Architecture Improvements

## Overview

Based on your excellent suggestions, here are the architectural improvements for the Memory Agent:

## 1. Single Responsibility Principle (SRP)

### Problem
The original `process_user_prompt` function was doing too much:
- Retrieving context
- Analyzing content  
- Storing memories
- Generating responses
- Storing responses

### Solution: MemoryOrchestrator Class

```python
class MemoryOrchestrator:
    async def store_memory()      # Only stores
    async def retrieve_memories() # Only retrieves
    async def get_context()       # Only builds context
    async def generate_response() # Only generates responses
    async def analyze_content()   # Only analyzes
```

Each method now has a single, clear responsibility.

### Benefits
- Easier to test individual components
- More maintainable code
- Better error isolation
- Clearer API design

## 2. Hierarchical Memory Types

### Problem
Flat memory types (FACT, PREFERENCE, etc.) were too limiting and didn't capture relationships.

### Solution: HierarchicalMemoryType System

```python
type_tree = {
    "personal": {
        "identity": ["name", "age", "location"],
        "preference": ["food", "music", "activity"],
        "profession": ["job", "company", "role"]
    },
    "knowledge": {
        "fact": ["general", "specific"],
        "skill": ["technical", "soft"],
        "experience": ["work", "personal"]
    },
    "temporal": {
        "conversation": ["question", "statement", "greeting"],
        "context": ["current", "past", "future"]
    }
}
```

### Features
- **3-level hierarchy**: major/minor/detail (대분류/중분류/소분류)
- **Path-based classification**: "personal/identity/name"
- **Related type discovery**: Find semantically related memories
- **Context-aware classification**: Uses previous classifications to improve accuracy
- **Storage strategies**: Different strategies for different types

### Benefits
- More nuanced memory organization
- Better retrieval through relationships
- Flexible classification system
- Storage optimization per type

## 3. Event Streaming Support

### Problem
No real-time updates for memory operations.

### Solution: Memory Event Streaming

```python
# Event types
- memory_created
- memory_updated  
- memory_deleted
- memory_retrieved

# Subscription options
- By user_id
- By session_id
- Global (all events)
```

### Implementation Options

#### SSE (Server-Sent Events)
```python
async def create_sse_stream(user_id: str):
    async for event in memory_event_stream.subscribe_user(user_id):
        yield event.to_sse()
```

#### WebSocket
```python
async def handle_websocket(websocket, user_id: str):
    async for event in memory_event_stream.subscribe_user(user_id):
        await websocket.send_json(event)
```

#### Long Polling (MCP Compatible)
```python
@mcp.tool
async def subscribe_memory_updates(user_id: str, duration: int):
    # Collect events for duration
    return events
```

### Benefits
- Real-time memory updates
- Event-driven architecture
- Better UX for collaborative apps
- Monitoring and debugging

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        Memory Agent                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────────┐  ┌──────────────────┐  ┌────────────┐ │
│  │ Memory          │  │ Hierarchical     │  │ Event      │ │
│  │ Orchestrator    │  │ Memory Types     │  │ Streaming  │ │
│  │                 │  │                  │  │            │ │
│  │ • store()       │  │ • classify()     │  │ • emit()   │ │
│  │ • retrieve()    │  │ • get_importance │  │ • subscribe│ │
│  │ • get_context() │  │ • get_strategy() │  │            │ │
│  └────────┬────────┘  └──────────────────┘  └────────────┘ │
│           │                                                  │
│           ▼                                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                   Storage Layer                      │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │   │
│  │  │ RAG-MCP  │  │  DB-MCP  │  │ Model-MCP (LLM) │  │   │
│  │  └──────────┘  └──────────┘  └──────────────────┘  │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Usage Examples

### 1. Store with Hierarchical Classification
```python
result = await store_memory(
    user_id="john",
    content="저는 서울에 살고 있는 30살 개발자입니다",
    # Automatically classified as: personal/identity/location + personal/profession/job
)
```

### 2. Retrieve with Related Types
```python
memories = await retrieve_memories(
    user_id="john",
    query="직업",
    memory_types=["personal/profession/job"],
    include_related=True  # Also searches knowledge/skill, knowledge/experience
)
```

### 3. Stream Real-time Updates
```python
# Client subscribes to updates
async for event in subscribe_memory_updates(user_id="john"):
    if event.event_type == "memory_created":
        print(f"New memory: {event.content}")
```

## Migration Path

1. **Phase 1**: Implement MemoryOrchestrator alongside existing code
2. **Phase 2**: Add hierarchical types with backward compatibility
3. **Phase 3**: Enable event streaming for new operations
4. **Phase 4**: Deprecate old `process_user_prompt` function

## Benefits Summary

1. **Better Code Organization**: Each component has one job
2. **Richer Memory Model**: Hierarchical classification captures relationships  
3. **Real-time Capabilities**: Event streaming enables reactive UIs
4. **Improved Retrieval**: Related type discovery improves search
5. **Future-proof**: Extensible architecture for new features