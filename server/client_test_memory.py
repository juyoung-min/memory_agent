#!/usr/bin/env python3
"""
Simple client to test Memory Agent conversation storage
"""

import asyncio
import httpx
import json
import uuid
from datetime import datetime

async def test_memory_conversation():
    """Test conversation storage and retrieval"""
    
    base_url = "http://localhost:8094"
    user_id = f"test_user_{uuid.uuid4().hex[:8]}"
    session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    print(f"Testing Memory Agent")
    print(f"User ID: {user_id}")
    print(f"Session ID: {session_id}")
    print("="*50)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Connect to SSE endpoint
        print("\n1. Connecting to Memory Agent...")
        
        sse_url = f"{base_url}/sse"
        async with client.stream('GET', sse_url) as response:
            # Get initial connection
            session_info = None
            async for line in response.aiter_lines():
                if line.startswith('data:'):
                    data = json.loads(line[5:])
                    if data.get('method') == 'initialize':
                        session_info = data
                        break
        
        # Create a unique session for messages
        msg_session_id = str(uuid.uuid4())
        messages_url = f"{base_url}/messages/?session_id={msg_session_id}"
        
        # Helper function to call tools
        async def call_tool(tool_name, arguments):
            request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                },
                "id": str(uuid.uuid4())
            }
            
            # Send request
            await client.post(messages_url, json=request)
            
            # Get response from SSE
            async with client.stream('GET', sse_url) as response:
                async for line in response.aiter_lines():
                    if line.startswith('data:'):
                        try:
                            data = json.loads(line[5:])
                            if data.get('id') == request['id']:
                                return data.get('result')
                        except:
                            continue
            return None
        
        # Store conversations
        print("\n2. Storing conversations...")
        conversations = [
            "안녕하세요! 저는 서울에 살고 있습니다.",
            "오늘 날씨가 정말 좋네요. 미세먼지도 없고요.",
            "내일 비가 온다고 하던데, 우산을 챙겨야겠어요.",
            "저는 개발자이고 Python을 주로 사용합니다.",
            "주말에는 등산을 가려고 계획 중이에요."
        ]
        
        for i, message in enumerate(conversations):
            print(f"\n   Message {i+1}: {message}")
            
            result = await call_tool(
                "process_user_prompt",
                {
                    "user_id": user_id,
                    "prompt": message,
                    "session_id": session_id,
                    "auto_store": True,
                    "generate_response": True
                }
            )
            
            if result:
                print(f"   Stored: ✓")
                if 'response' in result:
                    print(f"   AI Response: {result['response'][:100]}...")
            
            await asyncio.sleep(0.5)
        
        # Search conversations
        print("\n\n3. Searching conversations...")
        search_terms = ["날씨", "서울", "Python"]
        
        for term in search_terms:
            print(f"\n   Searching for: '{term}'")
            
            result = await call_tool(
                "get_conversation_history",
                {
                    "user_id": user_id,
                    "query": term,
                    "limit": 5
                }
            )
            
            if result and result.get('success'):
                conversations = result.get('conversations', [])
                print(f"   Found: {len(conversations)} matches")
                for conv in conversations[:3]:
                    print(f"     - {conv.get('content', '')[:80]}...")
                    print(f"       Similarity: {conv.get('similarity', 0):.2f}")
        
        # Get memory statistics
        print("\n\n4. Memory Statistics...")
        stats_result = await call_tool(
            "get_user_memory_stats",
            {
                "user_id": user_id
            }
        )
        
        if stats_result and stats_result.get('success'):
            stats = stats_result.get('stats', {})
            print(f"   Total memories: {stats.get('total_memories', 0)}")
            print(f"   Memory types: {json.dumps(stats.get('type_distribution', {}), ensure_ascii=False)}")

# Quick test function
async def quick_test():
    """Quick test to store and search a conversation"""
    
    print("Quick Memory Test")
    print("="*30)
    
    # Use the client-memory.py approach with proper SSE handling
    user_id = "quick_test_user"
    session_id = f"quick_{datetime.now().strftime('%H%M%S')}"
    
    # Store a message
    print(f"\nStoring message for user: {user_id}")
    
    # Direct HTTP call for testing
    async with httpx.AsyncClient() as client:
        # This would need proper SSE implementation
        # For now, showing the structure
        print("Message: '오늘 날씨가 참 좋네요!'")
        print("Stored: [Would store via SSE]")
        
        print("\nSearching for '날씨'...")
        print("Found: [Would search via SSE]")
    
    print("\nFor full test, run: python client_test_memory.py")

if __name__ == "__main__":
    # Run the quick test
    asyncio.run(quick_test())
    
    print("\n" + "="*50)
    print("To run full test with proper SSE:")
    print("1. Make sure docker containers are running")
    print("2. Use the original client-memory.py")
    print("3. Or check database directly with test_db_direct.py")