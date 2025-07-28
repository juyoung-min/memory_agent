#!/usr/bin/env python3
"""
Test Memory Agent MCP integration with RAG-MCP
Tests the full communication chain: Memory Agent → RAG-MCP → DB-MCP → Model-MCP
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import Memory Agent components
from src.memory_agent import MemoryAgent, MemoryType
from src.clients import InternalMCPClient
from src.config import get_config

class MemoryRAGIntegrationTest:
    """Test suite for Memory Agent → RAG-MCP integration"""
    
    def __init__(self):
        self.config = get_config()
        self.memory_agent = MemoryAgent(enable_intelligence=True)
        
        # Initialize clients
        self.rag_client = InternalMCPClient("http://mcp-rag:8093/sse", timeout=30)
        self.db_client = InternalMCPClient("http://mcp-db:8092/sse", timeout=30)
        self.model_client = InternalMCPClient("http://model-mcp:8091/sse", timeout=30)
        
        # Test data
        self.test_user_id = "test_user_integration"
        self.test_session_id = f"test_session_{int(datetime.now().timestamp())}"
        
    async def test_store_conversation_in_rag(self):
        """Test storing conversation memories in RAG-MCP"""
        logger.info("\n" + "="*80)
        logger.info("Test 1: Store Conversation in RAG-MCP")
        logger.info("="*80)
        
        conversations = [
            "안녕하세요, 저는 김철수입니다. Python 개발자입니다.",
            "최근에 FastAPI로 마이크로서비스를 구축했습니다.",
            "비동기 프로그래밍에 관심이 많습니다.",
            "다음 프로젝트에서는 Rust를 사용해보고 싶습니다."
        ]
        
        stored_ids = []
        
        for i, conv in enumerate(conversations):
            logger.info(f"\n📝 Storing conversation {i+1}: '{conv[:50]}...'")
            
            # Store in RAG-MCP
            result = await self.rag_client.call_tool(
                "rag_save_document",
                {
                    "content": conv,
                    "namespace": f"{self.test_user_id}_conversations",
                    "document_id": f"conv_{self.test_session_id}_{i}",
                    "metadata": {
                        "user_id": self.test_user_id,
                        "session_id": self.test_session_id,
                        "memory_type": "conversation",
                        "timestamp": datetime.utcnow().isoformat(),
                        "sequence": i
                    },
                    "chunk": False
                }
            )
            
            if result.get("success"):
                logger.info(f"✅ Stored successfully with ID: {result.get('document_id')}")
                stored_ids.append(result.get('document_id'))
            else:
                logger.error(f"❌ Failed to store: {result.get('error')}")
        
        return stored_ids
    
    async def test_search_conversations(self, stored_ids: List[str]):
        """Test searching conversations from RAG-MCP"""
        logger.info("\n" + "="*80)
        logger.info("Test 2: Search Conversations from RAG-MCP")
        logger.info("="*80)
        
        search_queries = [
            "Python 개발자",
            "FastAPI",
            "비동기",
            "Rust",
            "마이크로서비스"
        ]
        
        for query in search_queries:
            logger.info(f"\n🔍 Searching for: '{query}'")
            
            result = await self.rag_client.call_tool(
                "rag_search",
                {
                    "query": query,
                    "namespace": f"{self.test_user_id}_conversations",
                    "limit": 5,
                    "include_content": True,
                    "similarity_threshold": 0.5
                }
            )
            
            if result.get("success"):
                results = result.get("results", [])
                logger.info(f"📊 Found {len(results)} results:")
                for r in results:
                    logger.info(f"   - Score: {r.get('similarity'):.3f} | {r.get('content')[:60]}...")
            else:
                logger.error(f"❌ Search failed: {result.get('error')}")
    
    async def test_memory_agent_with_rag(self):
        """Test Memory Agent's automatic RAG integration"""
        logger.info("\n" + "="*80)
        logger.info("Test 3: Memory Agent Automatic RAG Storage")
        logger.info("="*80)
        
        # Test messages with different types
        test_messages = [
            ("저는 서울에서 일하는 백엔드 개발자입니다.", MemoryType.IDENTITY),
            ("주로 Python과 Go를 사용합니다.", MemoryType.SKILL),
            ("어제 회의에서 새로운 아키텍처를 논의했습니다.", MemoryType.CONVERSATION),
            ("주말에는 등산을 즐깁니다.", MemoryType.HOBBY),
            ("내년 목표는 시스템 설계 능력을 향상시키는 것입니다.", MemoryType.GOAL)
        ]
        
        for message, expected_type in test_messages:
            logger.info(f"\n📝 Processing: '{message}'")
            logger.info(f"   Expected type: {expected_type.value}")
            
            # Add memory through Memory Agent
            result = await self.memory_agent.add_memory(
                user_id=self.test_user_id,
                session_id=self.test_session_id,
                content=message,
                memory_type=None,  # Let it auto-classify
                importance=None
            )
            
            if result['status'] == 'success':
                logger.info(f"✅ Stored as: {result['memory_type']} (importance: {result['importance']})")
                
                # If it's a conversation type, verify it's in RAG
                if result['memory_type'] == 'conversation':
                    logger.info("   Checking RAG storage...")
                    search_result = await self.rag_client.call_tool(
                        "rag_search",
                        {
                            "query": message,
                            "namespace": f"{self.test_user_id}_conversations",
                            "limit": 1,
                            "include_content": True
                        }
                    )
                    if search_result.get("success") and search_result.get("results"):
                        logger.info("   ✅ Confirmed in RAG storage")
                    else:
                        logger.warning("   ⚠️ Not found in RAG storage")
    
    async def test_cross_session_retrieval(self):
        """Test retrieving memories across different sessions"""
        logger.info("\n" + "="*80)
        logger.info("Test 4: Cross-Session Memory Retrieval")
        logger.info("="*80)
        
        # Create memories in different sessions
        sessions = [
            f"session_morning_{datetime.now().strftime('%Y%m%d')}",
            f"session_afternoon_{datetime.now().strftime('%Y%m%d')}",
            f"session_evening_{datetime.now().strftime('%Y%m%d')}"
        ]
        
        session_messages = [
            "아침에 코드 리뷰를 진행했습니다.",
            "오후에 새로운 기능을 구현했습니다.",
            "저녁에 배포 준비를 완료했습니다."
        ]
        
        # Store messages in different sessions
        for session_id, message in zip(sessions, session_messages):
            logger.info(f"\n📝 Storing in {session_id}: '{message}'")
            
            await self.rag_client.call_tool(
                "rag_save_document",
                {
                    "content": message,
                    "namespace": f"{self.test_user_id}_conversations",
                    "document_id": f"{session_id}_memory",
                    "metadata": {
                        "user_id": self.test_user_id,
                        "session_id": session_id,
                        "memory_type": "conversation",
                        "timestamp": datetime.utcnow().isoformat()
                    },
                    "chunk": False
                }
            )
        
        # Search across all sessions
        logger.info("\n🔍 Searching across all sessions for '코드 배포'")
        result = await self.rag_client.call_tool(
            "rag_search",
            {
                "query": "코드 배포",
                "namespace": f"{self.test_user_id}_conversations",
                "limit": 10,
                "include_content": True
            }
        )
        
        if result.get("success"):
            results = result.get("results", [])
            logger.info(f"📊 Found {len(results)} results from different sessions:")
            for r in results:
                metadata = r.get("metadata", {})
                logger.info(f"   - Session: {metadata.get('session_id', 'unknown')}")
                logger.info(f"     Content: {r.get('content')}")
                logger.info(f"     Score: {r.get('similarity'):.3f}")
    
    async def test_embedding_generation(self):
        """Test embedding generation for memory content"""
        logger.info("\n" + "="*80)
        logger.info("Test 5: Embedding Generation for Memories")
        logger.info("="*80)
        
        test_content = "저는 5년차 Python 개발자이며, 마이크로서비스 아키텍처에 전문성이 있습니다."
        
        logger.info(f"📝 Generating embedding for: '{test_content}'")
        
        # Generate embedding through Model-MCP
        result = await self.model_client.call_tool(
            "generate_embedding",
            {
                "input": test_content,
                "model": "bge-m3"
            }
        )
        
        if result.get("success"):
            embedding = result.get("embedding", [])
            logger.info(f"✅ Generated embedding with dimension: {len(embedding)}")
            logger.info(f"   First 5 values: {embedding[:5]}")
            
            # Store with embedding in DB
            logger.info("\n💾 Storing in vector database...")
            store_result = await self.db_client.call_tool(
                "db_store_vector",
                {
                    "table": "memories",
                    "content": test_content,
                    "vector": embedding,
                    "metadata": {
                        "user_id": self.test_user_id,
                        "memory_type": "professional",
                        "test": True
                    }
                }
            )
            
            if store_result.get("success"):
                logger.info(f"✅ Stored with ID: {store_result.get('id')}")
                
                # Search by similarity
                logger.info("\n🔍 Searching by similarity...")
                search_result = await self.db_client.call_tool(
                    "db_search_vectors",
                    {
                        "table": "memories",
                        "query_vector": embedding,
                        "limit": 5,
                        "filters": {"user_id": self.test_user_id}
                    }
                )
                
                if search_result.get("success"):
                    results = search_result.get("results", [])
                    logger.info(f"📊 Found {len(results)} similar memories")
    
    async def test_answer_generation_with_context(self):
        """Test answer generation using memory context"""
        logger.info("\n" + "="*80)
        logger.info("Test 6: Answer Generation with Memory Context")
        logger.info("="*80)
        
        # First, ensure we have some context
        context_memories = [
            "저는 Python과 FastAPI를 주로 사용하는 백엔드 개발자입니다.",
            "마이크로서비스 아키텍처 설계 경험이 풍부합니다.",
            "최근에는 Kubernetes를 활용한 배포 자동화를 구축했습니다."
        ]
        
        # Store context
        for mem in context_memories:
            await self.rag_client.call_tool(
                "rag_save_document",
                {
                    "content": mem,
                    "namespace": f"{self.test_user_id}_conversations",
                    "metadata": {
                        "user_id": self.test_user_id,
                        "session_id": self.test_session_id,
                        "memory_type": "professional"
                    }
                }
            )
        
        # Now ask a question that requires context
        question = "제가 어떤 기술 스택을 사용하나요?"
        
        logger.info(f"\n❓ Question: {question}")
        
        # Use RAG to generate answer
        result = await self.rag_client.call_tool(
            "rag_answer",
            {
                "question": question,
                "namespace": f"{self.test_user_id}_conversations",
                "search_limit": 5,
                "model": "EXAONE-3.5-2.4B-Instruct"
            }
        )
        
        if result.get("success"):
            logger.info(f"✅ Generated answer:")
            logger.info(f"   {result.get('answer')}")
            logger.info(f"\n📚 Used sources:")
            for source in result.get("sources", []):
                logger.info(f"   - {source.get('content')[:80]}...")
    
    async def run_all_tests(self):
        """Run all integration tests"""
        logger.info("\n" + "="*80)
        logger.info("Memory Agent → RAG-MCP Integration Test Suite")
        logger.info("="*80)
        
        try:
            # Test 1: Store conversations
            stored_ids = await self.test_store_conversation_in_rag()
            
            # Test 2: Search conversations
            await self.test_search_conversations(stored_ids)
            
            # Test 3: Memory Agent automatic RAG storage
            await self.test_memory_agent_with_rag()
            
            # Test 4: Cross-session retrieval
            await self.test_cross_session_retrieval()
            
            # Test 5: Embedding generation
            await self.test_embedding_generation()
            
            # Test 6: Answer generation with context
            await self.test_answer_generation_with_context()
            
            logger.info("\n" + "="*80)
            logger.info("✅ All tests completed!")
            logger.info("="*80)
            
        except Exception as e:
            logger.error(f"\n❌ Test failed with error: {e}", exc_info=True)

async def main():
    """Main test runner"""
    test_suite = MemoryRAGIntegrationTest()
    await test_suite.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())