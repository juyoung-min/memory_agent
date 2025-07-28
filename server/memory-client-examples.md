# Memory Client Usage Examples

## 1. Store Operations

### Store with auto-classification
```bash
# Automatically classify and store
python client-memory-ops.py store --user-id john123 \
  --content "저는 서울에 살고 있는 개발자입니다"

# Store a preference
python client-memory-ops.py store --user-id john123 \
  --content "저는 커피보다 차를 더 좋아해요"

# Store a conversation
python client-memory-ops.py store --user-id john123 \
  --content "오늘 날씨가 정말 좋네요"
```

### Store with explicit type
```bash
# Store as fact
python client-memory-ops.py store --user-id john123 \
  --content "저는 Python과 JavaScript를 사용합니다" \
  --type skill

# Store as identity
python client-memory-ops.py store --user-id john123 \
  --content "제 이름은 김철수입니다" \
  --type identity

# Store as preference
python client-memory-ops.py store --user-id john123 \
  --content "아침형 인간이라 새벽에 일하는 걸 좋아해요" \
  --type preference
```

## 2. Retrieve Operations

### Search all memories
```bash
# Search for weather-related memories
python client-memory-ops.py retrieve --user-id john123 \
  --query "날씨"

# Search for development-related content
python client-memory-ops.py retrieve --user-id john123 \
  --query "개발" \
  --limit 5
```

### Search specific memory types
```bash
# Search only skills
python client-memory-ops.py retrieve --user-id john123 \
  --query "프로그래밍" \
  --types skill

# Search facts and preferences
python client-memory-ops.py retrieve --user-id john123 \
  --query "좋아" \
  --types fact preference

# Search within a specific session
python client-memory-ops.py retrieve --user-id john123 \
  --query "오늘" \
  --session-id session_20240723_143000
```

## 3. Delete Operations

```bash
# Delete a specific memory by ID
python client-memory-ops.py delete --user-id john123 \
  --memory-id "a2d0668b-1249-4ab3-b069-bb8f31790dcf"
```

## 4. Statistics Operations

```bash
# Get overall memory statistics
python client-memory-ops.py stats --user-id john123

# Get statistics for a specific session
python client-memory-ops.py stats --user-id john123 \
  --session-id session_20240723_143000
```

## Memory Types

Available memory types for explicit storage:
- `identity` - Personal identity information (name, age, etc.)
- `profession` - Job, career, work-related
- `skill` - Technical skills, abilities
- `fact` - General facts about the user
- `preference` - Likes, dislikes, preferences
- `goal` - Goals, aspirations
- `hobby` - Hobbies, interests
- `experience` - Past experiences
- `context` - Contextual information
- `conversation` - Chat conversations

## Advanced Examples

### Batch operations
```bash
# Store multiple memories
for content in "저는 개발자입니다" "Python을 주로 사용합니다" "5년 경력이 있습니다"; do
  python client-memory-ops.py store --user-id john123 --content "$content"
done

# Search and filter results
python client-memory-ops.py retrieve --user-id john123 \
  --query "경력" \
  --types profession experience \
  --limit 20
```

### Session management
```bash
# Create a session ID
SESSION_ID="session_$(date +%Y%m%d_%H%M%S)"

# Store memories in the same session
python client-memory-ops.py store --user-id john123 \
  --content "프로젝트 미팅을 시작합니다" \
  --session-id $SESSION_ID

python client-memory-ops.py store --user-id john123 \
  --content "다음 주까지 API 설계를 완료해야 합니다" \
  --session-id $SESSION_ID \
  --type goal

# Retrieve session-specific memories
python client-memory-ops.py retrieve --user-id john123 \
  --query "프로젝트" \
  --session-id $SESSION_ID
```