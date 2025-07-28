#!/usr/bin/env python3
"""
Demo: Memory Agent Core Functionality
Shows how the Memory Agent works internally
"""

import asyncio
from datetime import datetime
from src.memory_agent import MemoryAgent, MemoryType, Memory

async def demo():
    print("=" * 80)
    print("Memory Agent Demo - Core Functionality")
    print("=" * 80)
    
    # Create memory agent
    agent = MemoryAgent(enable_intelligence=True)
    print("✅ Memory Agent created with intelligence enabled\n")
    
    # Test data
    user_id = "demo_user"
    session_id = f"demo_{int(datetime.now().timestamp())}"
    
    # Demo messages with different types
    test_messages = [
        ("저는 김철수입니다. 파이썬 개발자로 5년째 일하고 있습니다.", "Identity & Profession"),
        ("FastAPI를 주로 사용하고, async 프로그래밍을 선호합니다.", "Skills & Preferences"),
        ("최근에 대규모 마이크로서비스 프로젝트를 완료했습니다.", "Experience"),
        ("내년에는 Rust를 배워보고 싶습니다.", "Goals"),
        ("주말에는 등산을 즐깁니다.", "Hobby"),
        ("오늘 날씨 어때?", "Trivial - should not store"),
    ]
    
    print(f"Processing {len(test_messages)} test messages...\n")
    
    for message, description in test_messages:
        print(f"📝 Message: '{message}'")
        print(f"   Type: {description}")
        
        # Add memory using the agent
        result = await agent.add_memory(
            user_id=user_id,
            session_id=session_id,
            content=message,
            memory_type=None,  # Auto-classify
            importance=None    # Auto-calculate
        )
        
        print(f"   ➡️ Status: {result['status']}")
        if result['status'] == 'success':
            print(f"   📊 Detected Type: {result['memory_type']}")
            print(f"   ⭐ Importance: {result['importance']}/10")
            print(f"   🆔 Memory ID: {result['memory_id'][:20]}...")
            
            # Show extracted info if available
            if 'extracted_info' in result:
                info = result['extracted_info']
                if info.get('entities'):
                    print(f"   🏷️ Entities: {info['entities']}")
        print()
    
    # Get memory statistics
    print("\n" + "=" * 80)
    print("Memory Statistics")
    print("=" * 80)
    
    stats = await agent.storage.get_memory_stats(user_id, session_id)
    print(f"📊 Total memories stored: {stats['total_memories']}")
    print(f"📈 Average importance: {stats['average_importance']}")
    print(f"📋 Type distribution:")
    for mem_type, count in stats['type_distribution'].items():
        print(f"   - {mem_type}: {count}")
    
    # Search memories
    print("\n" + "=" * 80)
    print("Memory Search Demo")
    print("=" * 80)
    
    # Search for Python-related memories
    search_results = await agent.storage.search_memories(
        user_id=user_id,
        session_id=session_id,
        query="파이썬",
        limit=5
    )
    
    print(f"🔍 Search for '파이썬' found {len(search_results)} results:")
    for i, memory in enumerate(search_results, 1):
        print(f"{i}. [{memory.type.value}] {memory.content[:50]}...")
        print(f"   Importance: {memory.importance}/10")
    
    # Search by type
    print("\n🔍 Search for SKILL type memories:")
    skill_memories = await agent.storage.search_memories(
        user_id=user_id,
        session_id=session_id,
        memory_types=[MemoryType.SKILL],
        limit=5
    )
    
    for i, memory in enumerate(skill_memories, 1):
        print(f"{i}. {memory.content}")
    
    # Test intelligence decision making
    print("\n" + "=" * 80)
    print("Intelligence Layer Demo")
    print("=" * 80)
    
    test_phrases = [
        "안녕하세요",
        "저는 서울에 살고 있습니다",
        "날씨가 좋네요",
        "파이썬으로 웹 개발을 하고 있어요",
        "내일 회의가 있어요"
    ]
    
    for phrase in test_phrases:
        should_store = agent.intelligence.should_store(phrase)
        mem_type = agent.intelligence.extract_memory_type(phrase)
        importance = agent.intelligence.calculate_importance(phrase, mem_type, {})
        
        print(f"📝 '{phrase}'")
        print(f"   Should store: {'✅ Yes' if should_store else '❌ No'}")
        print(f"   Type: {mem_type.value}")
        print(f"   Importance: {importance}/10")

if __name__ == "__main__":
    asyncio.run(demo())