#!/usr/bin/env python3
"""
Quick test for chat storage - using direct database
"""

import subprocess
import time
import json

def run_command(cmd):
    """Run a command and return output"""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout

print("=== Quick Chat Storage Test ===\n")

# 1. Check current memories
print("1. Current memories in database:")
output = run_command('docker exec postgres-vector psql -U postgres -d vector_db -c "SELECT COUNT(*) as total FROM memories;"')
print(output)

# 2. Show recent conversations
print("\n2. Recent conversations:")
output = run_command('''docker exec postgres-vector psql -U postgres -d vector_db -c "SELECT id, LEFT(content, 80) as content_preview, created_at FROM memories ORDER BY created_at DESC LIMIT 5;"''')
print(output)

# 3. Search for weather-related content
print("\n3. Weather-related conversations:")
output = run_command('''docker exec postgres-vector psql -U postgres -d vector_db -c "SELECT LEFT(content, 100) as content, metadata->>'user_id' as user FROM memories WHERE content LIKE '%날씨%' OR content LIKE '%weather%' LIMIT 5;"''')
print(output)

# 4. Check namespaces
print("\n4. Memory namespaces (RAG collections):")
output = run_command('''docker exec postgres-vector psql -U postgres -d vector_db -c "SELECT DISTINCT metadata->>'namespace' as namespace, COUNT(*) as count FROM memories WHERE metadata->>'namespace' IS NOT NULL GROUP BY metadata->>'namespace';"''')
print(output)

# 5. User-specific memories
print("\n5. User-specific conversation counts:")
output = run_command('''docker exec postgres-vector psql -U postgres -d vector_db -c "SELECT metadata->>'user_id' as user_id, COUNT(*) as memory_count FROM memories WHERE metadata->>'user_id' IS NOT NULL GROUP BY metadata->>'user_id';"''')
print(output)

print("\n=== Test Complete ===")
print("\nTo store new conversations:")
print("1. Use the Memory Agent API with process_user_prompt")
print("2. Messages are automatically classified and stored")
print("3. Conversations are indexed in RAG-MCP for retrieval")
print("\nTo search conversations:")
print("1. Use get_conversation_history with a search query")
print("2. Results are ranked by vector similarity")
print("3. Can filter by user_id and session_id")