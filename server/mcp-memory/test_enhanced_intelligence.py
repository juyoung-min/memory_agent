"""
Test script for Enhanced Intelligence features
Demonstrates content processing, entity extraction, and storage strategies
"""

import asyncio
import json
from datetime import datetime

from src.memory_agent.enhanced_intelligence import EnhancedMemoryIntelligence
from src.memory_agent.memory_types import MemoryType
from src.storage_strategy import StorageStrategyDeterminer

async def test_enhanced_intelligence():
    """Test enhanced intelligence features"""
    
    # Initialize components
    intelligence = EnhancedMemoryIntelligence()
    strategy_determiner = StorageStrategyDeterminer()
    
    # Test cases
    test_cases = [
        {
            "content": "제 이름은 김철수입니다. 서울에 살고 있는 30살 개발자예요.",
            "expected_type": MemoryType.IDENTITY,
            "description": "Identity information with name, age, location"
        },
        {
            "content": "오늘 날씨가 어때요?",
            "expected_type": MemoryType.CONVERSATION,
            "description": "Simple question about weather"
        },
        {
            "content": "저는 Python과 JavaScript를 사용할 수 있고, Docker와 Kubernetes에 전문가입니다.",
            "expected_type": MemoryType.SKILL,
            "description": "Skills and expertise"
        },
        {
            "content": "저는 매운 음식을 좋아해요. 특히 김치찌개를 즐겨 먹습니다.",
            "expected_type": MemoryType.PREFERENCE,
            "description": "Food preferences"
        },
        {
            "content": "작년에 제주도 여행을 갔었는데, 한라산 등반이 정말 힘들었지만 보람있었어요. 정상에서 본 경치가 잊을 수 없습니다.",
            "expected_type": MemoryType.EXPERIENCE,
            "description": "Travel experience"
        }
    ]
    
    print("=" * 80)
    print("Enhanced Intelligence Test Results")
    print("=" * 80)
    
    for i, test in enumerate(test_cases, 1):
        print(f"\nTest Case {i}: {test['description']}")
        print(f"Content: {test['content']}")
        print("-" * 40)
        
        # Extract memory type
        detected_type = intelligence.extract_memory_type(test['content'], {})
        print(f"Detected Type: {detected_type.value} (Expected: {test['expected_type'].value})")
        
        # Process content
        processed = intelligence.process_content_for_storage(
            content=test['content'],
            memory_type=detected_type,
            context={
                "user_id": "test_user",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
        print(f"Should Store: {processed.should_store}")
        print(f"Importance: {processed.importance}/10")
        print(f"Storage Format: {processed.storage_format}")
        
        # Keywords
        if processed.keywords:
            print(f"Keywords: {', '.join(processed.keywords[:5])}")
        
        # Entities
        if processed.extracted_entities:
            print("Extracted Entities:")
            for entity in processed.extracted_entities[:3]:
                print(f"  - {entity['type']}: {entity['value']} (confidence: {entity['confidence']})")
        
        # Summary
        if processed.summary and processed.summary != test['content']:
            print(f"Summary: {processed.summary}")
        
        # Storage strategy
        strategy = strategy_determiner.determine_strategy(
            memory_type=detected_type.value,
            importance=processed.importance,
            content_size=len(test['content'])
        )
        
        print(f"Storage Strategy:")
        print(f"  - Primary: {strategy.primary_location.value}")
        print(f"  - RAG Enabled: {strategy.includes_rag}")
        print(f"  - Embedding: {strategy.includes_embedding}")
        print(f"  - Compression: {strategy.compression_enabled}")
        
        # Cost estimation
        cost = strategy_determiner.get_storage_cost(strategy, len(test['content']))
        print(f"  - Estimated Cost: {cost['total_monthly']} units/month")
        
        # Structured content preview
        if processed.storage_format == "json":
            try:
                structured = json.loads(processed.structured_content)
                print(f"Structured Data: {json.dumps(structured, ensure_ascii=False, indent=2)}")
            except:
                print(f"Structured Content: {processed.structured_content[:100]}...")
        else:
            print(f"Processed Content: {processed.structured_content[:100]}...")

    print("\n" + "=" * 80)
    print("Special Processing Tests")
    print("=" * 80)
    
    # Test conversation detection
    conversations = [
        "내가 방금 어떤 질문했죠?",
        "안녕하세요! 오늘 기분이 어떠세요?",
        "감사합니다. 도움이 되었어요.",
        "그래서 결론이 뭔가요?"
    ]
    
    print("\nConversation Detection:")
    for conv in conversations:
        detected = intelligence.extract_memory_type(conv, {})
        processed = intelligence.process_content_for_storage(conv, detected, {})
        print(f"  '{conv}' -> Type: {detected.value}, Importance: {processed.importance}")
    
    # Test fact extraction
    facts = [
        "파이썬은 1991년에 귀도 반 로섬이 개발했습니다.",
        "서울의 인구는 약 950만명입니다.",
        "물의 끓는점은 100도입니다."
    ]
    
    print("\nFact Processing:")
    for fact in facts:
        detected = intelligence.extract_memory_type(fact, {})
        processed = intelligence.process_content_for_storage(fact, detected, {})
        print(f"  '{fact}'")
        print(f"    -> Structured: {processed.structured_content}")
        print(f"    -> Importance: {processed.importance}")

if __name__ == "__main__":
    asyncio.run(test_enhanced_intelligence())