# Autonomous Memory Agent Guide

## Philosophy

The Memory Agent is designed to be **autonomous and intelligent**. When you send a message, it automatically:

1. **Analyzes** your message to understand intent
2. **Retrieves** relevant context from memory
3. **Stores** important information appropriately
4. **Generates** intelligent responses

You don't need to tell it what action to take - it figures that out on its own!

## How It Works

When you send a message like "내가 방금 어떤 질문했죠?" (What did I just ask?), the Memory Agent:

1. **Recognizes** this is asking about previous conversation
2. **Searches** conversation history automatically
3. **Retrieves** the most relevant previous messages
4. **Generates** a response based on that context
5. **Stores** this new interaction for future reference

## Using the Autonomous Client

### Option 1: Autonomous Client (Recommended)

```bash
# Single message
uv run python client-memory-auto.py --user-id test_user --message "내가 방금 어떤 질문했죠?"

# Interactive mode
uv run python client-memory-auto.py --user-id test_user
```

In interactive mode:
- Just type your messages naturally
- Type 'stats' to see your memory statistics
- Type 'exit' to quit

### Option 2: Updated Original Client

The original client now supports the 'chat' action:

```bash
# Chat action (autonomous processing)
uv run python client-memory.py --action chat --user-id test_user --message "내가 방금 어떤 질문했죠?"
```

But you can still use specific actions if needed:
```bash
# Store specific memory
uv run python client-memory.py --action store --user-id test_user --message "저는 Python 개발자입니다" --type profession

# Search memories
uv run python client-memory.py --action search --user-id test_user --message "Python"

# Get conversation history
uv run python client-memory.py --action history --user-id test_user
```

## Examples

### Natural Conversation
```
You: 안녕하세요! 저는 김철수입니다.
Agent: 안녕하세요, 김철수님! 만나서 반갑습니다.
[Agent stores: identity information]

You: 저는 서울에 살고 있는 Python 개발자예요.
Agent: 서울에서 Python 개발자로 일하고 계시는군요! 
[Agent stores: location, profession, skills]

You: 제가 어떤 일을 한다고 했죠?
Agent: Python 개발자라고 하셨습니다. 서울에서 일하고 계시다고 하셨어요.
[Agent retrieves: previous context and responds accurately]
```

### Memory Operations Behind the Scenes

When you send "제가 어떤 일을 한다고 했죠?", the agent:

```json
{
  "memory_operations": {
    "context_found": {
      "conversations": 2,
      "memories": 1
    },
    "prompt_analysis": {
      "detected_type": "conversation",
      "importance": 7.0,
      "stored": true
    }
  }
}
```

## Benefits of Autonomous Approach

1. **Natural Interaction**: Talk naturally without thinking about commands
2. **Intelligent Context**: Agent knows when to retrieve vs store
3. **Automatic Classification**: Memories are organized automatically
4. **Seamless Experience**: Focus on conversation, not operations

## Technical Details

The autonomous flow uses `process_user_prompt` which:

```python
# 1. Analyzes prompt
memory_type = detect_type(prompt)  # conversation, question, fact, etc.

# 2. Retrieves context
relevant_memories = search_memories(prompt)
conversation_history = get_recent_conversations()

# 3. Generates response
response = generate_with_context(prompt, context)

# 4. Stores interaction
store_memory(prompt, memory_type)
store_memory(response, "conversation")
```

## When to Use Specific Actions

While autonomous mode is recommended, specific actions are useful for:

- **Bulk Import**: Store many memories with specific types
- **Debugging**: Check what's stored in memory
- **Administration**: Delete or update specific memories
- **Testing**: Verify memory operations work correctly

## Architecture

```
User Message
    ↓
Memory Agent (Autonomous)
    ├── Intelligence Layer (Analyze)
    ├── Storage Strategy (Decide)
    ├── Vector Search (Retrieve)
    ├── Enhanced Processing (Structure)
    └── Response Generation (Respond)
    ↓
Response + Memory Management
```

The Memory Agent acts as an intelligent assistant that manages its own memory, making decisions about what to remember and when to recall it - just like a human would!