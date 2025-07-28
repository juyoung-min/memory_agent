#!/usr/bin/env python3
"""
Mock test for Memory Agent → RAG-MCP communication
Tests the integration logic without requiring actual services
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MockMCPClient:
    """Mock MCP client for testing"""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.stored_data = {}  # In-memory storage for mocking
        
    async def call_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Mock tool calls with realistic responses"""
        logger.info(f"[{self.service_name}] Mock call to {tool_name}")
        logger.debug(f"  Parameters: {json.dumps(params, indent=2, ensure_ascii=False)}")
        
        # Mock different tool responses
        if self.service_name == "RAG-MCP":
            if tool_name == "rag_save_document":
                doc_id = params.get("document_id", f"doc_{datetime.now().timestamp()}")
                self.stored_data[doc_id] = {
                    "content": params.get("content"),
                    "metadata": params.get("metadata", {}),
                    "namespace": params.get("namespace")
                }
                return {
                    "success": True,
                    "document_id": doc_id,
                    "chunks_created": 1
                }
            
            elif tool_name == "rag_search":
                # Simulate search results
                query = params.get("query", "").lower()
                results = []
                
                for doc_id, doc in self.stored_data.items():
                    content = doc.get("content", "").lower()
                    if query in content:
                        results.append({
                            "content": doc["content"],
                            "similarity": 0.85,  # Mock similarity score
                            "metadata": doc["metadata"],
                            "document_id": doc_id
                        })
                
                return {
                    "success": True,
                    "results": results[:params.get("limit", 5)],
                    "total": len(results)
                }
            
            elif tool_name == "rag_answer":
                # Mock answer generation
                question = params.get("question", "")
                return {
                    "success": True,
                    "answer": f"Based on your history: You are a Python developer who uses FastAPI.",
                    "sources": [
                        {"content": "저는 Python 개발자입니다", "similarity": 0.9},
                        {"content": "FastAPI를 주로 사용합니다", "similarity": 0.85}
                    ]
                }
        
        elif self.service_name == "Model-MCP":
            if tool_name == "generate_embedding":
                # Mock embedding generation
                return {
                    "success": True,
                    "embedding": [0.1, 0.2, 0.3, 0.4, 0.5] * 204,  # 1024-dim mock vector
                    "model": params.get("model", "bge-m3")
                }
            
            elif tool_name == "generate_completion":
                # Mock text generation
                return {
                    "success": True,
                    "text": "I understand you're a Python developer with FastAPI experience.",
                    "model": params.get("model", "EXAONE-3.5-2.4B-Instruct")
                }
        
        elif self.service_name == "DB-MCP":
            if tool_name == "db_store_vector":
                vec_id = f"vec_{datetime.now().timestamp()}"
                self.stored_data[vec_id] = {
                    "content": params.get("content"),
                    "vector": params.get("vector"),
                    "metadata": params.get("metadata", {})
                }
                return {
                    "success": True,
                    "id": vec_id
                }
            
            elif tool_name == "db_search_vectors":
                # Mock vector search
                return {
                    "success": True,
                    "results": [
                        {
                            "id": "vec_123",
                            "content": "Python developer with 5 years experience",
                            "similarity": 0.92,
                            "metadata": {"type": "professional"}
                        }
                    ]
                }
        
        return {"success": False, "error": f"Unknown tool: {tool_name}"}

class MemoryAgentRAGTest:
    """Test Memory Agent with RAG integration using mocks"""
    
    def __init__(self):
        # Create mock clients
        self.rag_client = MockMCPClient("RAG-MCP")
        self.model_client = MockMCPClient("Model-MCP")
        self.db_client = MockMCPClient("DB-MCP")
        
        # Test data
        self.user_id = "test_user"
        self.session_id = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    async def test_conversation_flow(self):
        """Test complete conversation flow through Memory Agent"""
        logger.info("\n" + "="*60)
        logger.info("Test: Complete Conversation Flow")
        logger.info("="*60)
        
        # Simulate user messages
        user_messages = [
            "안녕하세요, 저는 김철수입니다.",
            "Python으로 백엔드 개발을 하고 있습니다.",
            "FastAPI와 async 프로그래밍을 주로 사용합니다.",
            "최근에 마이크로서비스 프로젝트를 완료했습니다."
        ]
        
        # Process each message
        for i, message in enumerate(user_messages):
            logger.info(f"\n👤 User: {message}")
            
            # Step 1: Generate embedding for the message
            embedding_result = await self.model_client.call_tool(
                "generate_embedding",
                {"input": message, "model": "bge-m3"}
            )
            
            if embedding_result["success"]:
                logger.info("✅ Generated embedding")
            
            # Step 2: Store as conversation in RAG
            rag_result = await self.rag_client.call_tool(
                "rag_save_document",
                {
                    "content": message,
                    "namespace": f"{self.user_id}_conversations",
                    "document_id": f"conv_{self.session_id}_{i}",
                    "metadata": {
                        "user_id": self.user_id,
                        "session_id": self.session_id,
                        "memory_type": "conversation",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                }
            )
            
            if rag_result["success"]:
                logger.info(f"✅ Stored in RAG with ID: {rag_result['document_id']}")
            
            # Step 3: Also store important info in vector DB
            if any(keyword in message for keyword in ["김철수", "Python", "FastAPI"]):
                db_result = await self.db_client.call_tool(
                    "db_store_vector",
                    {
                        "table": "user_memories",
                        "content": message,
                        "vector": embedding_result.get("embedding"),
                        "metadata": {
                            "user_id": self.user_id,
                            "memory_type": "identity" if "김철수" in message else "skill"
                        }
                    }
                )
                
                if db_result["success"]:
                    logger.info(f"✅ Stored in vector DB with ID: {db_result['id']}")
    
    async def test_memory_retrieval(self):
        """Test retrieving memories using RAG search"""
        logger.info("\n" + "="*60)
        logger.info("Test: Memory Retrieval via RAG")
        logger.info("="*60)
        
        # Search queries
        queries = [
            ("Python", "기술 관련 검색"),
            ("프로젝트", "경험 관련 검색"),
            ("김철수", "신원 관련 검색")
        ]
        
        for query, description in queries:
            logger.info(f"\n🔍 {description}: '{query}'")
            
            # Search in RAG
            search_result = await self.rag_client.call_tool(
                "rag_search",
                {
                    "query": query,
                    "namespace": f"{self.user_id}_conversations",
                    "limit": 3,
                    "include_content": True
                }
            )
            
            if search_result["success"]:
                results = search_result.get("results", [])
                logger.info(f"📊 Found {len(results)} results:")
                for r in results:
                    logger.info(f"   - Score: {r['similarity']:.2f} | {r['content']}")
    
    async def test_answer_generation(self):
        """Test generating answers based on memory context"""
        logger.info("\n" + "="*60)
        logger.info("Test: Answer Generation with Context")
        logger.info("="*60)
        
        questions = [
            "제가 사용하는 프로그래밍 언어는 무엇인가요?",
            "제 이름이 뭐였죠?",
            "어떤 프로젝트를 했나요?"
        ]
        
        for question in questions:
            logger.info(f"\n❓ Question: {question}")
            
            # Generate answer using RAG
            answer_result = await self.rag_client.call_tool(
                "rag_answer",
                {
                    "question": question,
                    "namespace": f"{self.user_id}_conversations",
                    "search_limit": 5
                }
            )
            
            if answer_result["success"]:
                logger.info(f"💬 Answer: {answer_result['answer']}")
                logger.info("📚 Sources used:")
                for source in answer_result.get("sources", []):
                    logger.info(f"   - {source['content']}")
    
    async def test_full_prompt_processing(self):
        """Test full prompt processing as Memory Agent would do"""
        logger.info("\n" + "="*60)
        logger.info("Test: Full Prompt Processing Flow")
        logger.info("="*60)
        
        prompt = "저는 5년차 시니어 개발자이고, 다음 달에 새로운 프로젝트를 시작합니다."
        
        logger.info(f"👤 User prompt: {prompt}")
        
        # Step 1: Search for relevant past memories
        logger.info("\n1️⃣ Searching for relevant context...")
        search_result = await self.rag_client.call_tool(
            "rag_search",
            {
                "query": prompt,
                "namespace": f"{self.user_id}_conversations",
                "limit": 5
            }
        )
        
        context_memories = search_result.get("results", [])
        logger.info(f"   Found {len(context_memories)} relevant memories")
        
        # Step 2: Analyze and classify the prompt
        logger.info("\n2️⃣ Analyzing prompt...")
        # In real implementation, this would use intelligence module
        memory_type = "professional"  # Mock classification
        importance = 8.5  # Mock importance score
        logger.info(f"   Type: {memory_type}, Importance: {importance}/10")
        
        # Step 3: Store the prompt
        logger.info("\n3️⃣ Storing prompt as memory...")
        store_result = await self.rag_client.call_tool(
            "rag_save_document",
            {
                "content": f"User: {prompt}",
                "namespace": f"{self.user_id}_conversations",
                "metadata": {
                    "user_id": self.user_id,
                    "session_id": self.session_id,
                    "memory_type": memory_type,
                    "importance": importance,
                    "role": "user"
                }
            }
        )
        
        if store_result["success"]:
            logger.info(f"   ✅ Stored with ID: {store_result['document_id']}")
        
        # Step 4: Generate response
        logger.info("\n4️⃣ Generating response...")
        
        # Build context prompt
        context_parts = ["Based on your history:\n"]
        for mem in context_memories[:3]:
            context_parts.append(f"- {mem['content']}")
        
        full_prompt = "\n".join(context_parts) + f"\n\nCurrent: {prompt}\n\nResponse:"
        
        response_result = await self.model_client.call_tool(
            "generate_completion",
            {
                "prompt": full_prompt,
                "model": "EXAONE-3.5-2.4B-Instruct",
                "max_tokens": 200
            }
        )
        
        if response_result["success"]:
            response = response_result["text"]
            logger.info(f"   🤖 Assistant: {response}")
            
            # Step 5: Store the response
            logger.info("\n5️⃣ Storing response...")
            await self.rag_client.call_tool(
                "rag_save_document",
                {
                    "content": f"Assistant: {response}",
                    "namespace": f"{self.user_id}_conversations",
                    "metadata": {
                        "user_id": self.user_id,
                        "session_id": self.session_id,
                        "memory_type": "conversation",
                        "role": "assistant"
                    }
                }
            )
            logger.info("   ✅ Response stored")
    
    async def run_all_tests(self):
        """Run all mock tests"""
        try:
            await self.test_conversation_flow()
            await self.test_memory_retrieval()
            await self.test_answer_generation()
            await self.test_full_prompt_processing()
            
            logger.info("\n" + "="*60)
            logger.info("✅ All mock tests completed successfully!")
            logger.info("="*60)
            
        except Exception as e:
            logger.error(f"❌ Test failed: {e}", exc_info=True)

async def main():
    """Main test runner"""
    test = MemoryAgentRAGTest()
    await test.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())