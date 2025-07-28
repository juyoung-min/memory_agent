"""
Enhanced Memory Operations Client
Demonstrates enhanced intelligence features for memory management
"""

import asyncio
import json
from datetime import datetime
from mcp import ClientSession, SSEServerTransport
from httpx import AsyncClient, Limits

class EnhancedMemoryClient:
    def __init__(self, base_url="http://localhost:8094/sse"):
        self.base_url = base_url
        self.session = None
        self.http_client = None
        
    async def connect(self):
        """Connect to the Memory Agent MCP server"""
        self.http_client = AsyncClient(
            timeout=30.0,
            limits=Limits(max_keepalive_connections=1, max_connections=5),
        )
        
        sse_transport = SSEServerTransport(self.http_client, self.base_url)
        self.session = ClientSession(sse_transport)
        
        await self.session.initialize()
        print(f"Connected to Memory Agent (Enhanced)")
        
        # List available tools
        tools = await self.session.list_tools()
        enhanced_tools = [t.name for t in tools if 'enhanced' in t.name]
        print(f"Available enhanced tools: {', '.join(enhanced_tools)}")
        
        return True
    
    async def disconnect(self):
        """Disconnect from the server"""
        if self.http_client:
            await self.http_client.aclose()
        print("Disconnected from Memory Agent")
    
    async def process_message_enhanced(self, user_id: str, message: str, session_id: str):
        """Process message with enhanced intelligence"""
        result = await self.session.call_tool(
            "process_message_enhanced",
            {
                "user_id": user_id,
                "message": message,
                "session_id": session_id
            }
        )
        return json.loads(result.content)
    
    async def analyze_content(self, content: str, user_id: str = None):
        """Analyze content for storage recommendations"""
        result = await self.session.call_tool(
            "analyze_content_for_storage",
            {
                "content": content,
                "user_id": user_id
            }
        )
        return json.loads(result.content)
    
    async def process_prompt_enhanced(self, user_id: str, prompt: str, session_id: str):
        """Process user prompt with enhanced intelligence"""
        result = await self.session.call_tool(
            "process_user_prompt_enhanced",
            {
                "user_id": user_id,
                "prompt": prompt,
                "session_id": session_id,
                "auto_store": True,
                "generate_response": True
            }
        )
        return json.loads(result.content)

async def demo_enhanced_features():
    """Demonstrate enhanced intelligence features"""
    client = EnhancedMemoryClient()
    
    try:
        # Connect to server
        await client.connect()
        
        user_id = "demo_user"
        session_id = f"demo_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        print("\n" + "="*60)
        print("Enhanced Intelligence Demo")
        print("="*60)
        
        # Demo 1: Analyze different types of content
        print("\n1. Content Analysis Demo")
        print("-"*40)
        
        test_contents = [
            "제 이름은 박지민이고, 부산에서 온 28살 디자이너입니다.",
            "Python, React, Docker를 능숙하게 다루며, AWS 인증을 보유하고 있습니다.",
            "저는 커피보다 차를 선호하고, 특히 녹차를 즐겨 마십니다.",
            "작년 여름에 유럽 배낭여행을 다녀왔는데, 파리의 에펠탑이 가장 인상적이었어요.",
            "오늘 회의에서 논의한 프로젝트 일정을 다시 확인해주세요."
        ]
        
        for content in test_contents:
            print(f"\nAnalyzing: '{content[:50]}...'")
            analysis = await client.analyze_content(content, user_id)
            
            if analysis['success']:
                details = analysis['analysis']
                print(f"  Type: {details['detected_type']}")
                print(f"  Importance: {details['importance']}/10")
                print(f"  Should Store: {details['should_store']}")
                print(f"  Keywords: {', '.join(details['keywords'][:5])}")
                if details['entities']:
                    print(f"  Entities: {len(details['entities'])} found")
                    for entity in details['entities'][:3]:
                        print(f"    - {entity['type']}: {entity['value']}")
                if details.get('summary') and details['summary'] != content:
                    print(f"  Summary: {details['summary']}")
        
        # Demo 2: Store messages with enhanced processing
        print("\n\n2. Enhanced Storage Demo")
        print("-"*40)
        
        messages = [
            "안녕하세요! 저는 서울에 사는 김철수입니다. 프론트엔드 개발자로 5년째 일하고 있어요.",
            "React와 TypeScript를 주로 사용하고, 최근에는 Next.js를 공부하고 있습니다.",
            "매운 음식을 정말 좋아해서 주말마다 맛집을 찾아다녀요.",
            "어제 면접 본 회사에서 합격 통보를 받았어요! 너무 기뻐요.",
            "내일 오전 10시에 회의가 있다는 것 잊지 마세요."
        ]
        
        for msg in messages:
            print(f"\nProcessing: '{msg[:50]}...'")
            result = await client.process_message_enhanced(user_id, msg, session_id)
            
            if result['success']:
                print(f"  Stored as: {result['memory_type']}")
                print(f"  Importance: {result['importance']}")
                if result.get('processed'):
                    proc = result['processed']
                    print(f"  Format: {proc['storage_format']}")
                    print(f"  Keywords: {', '.join(proc['keywords'][:3])}")
                if result.get('storage_strategy'):
                    strategy = result['storage_strategy']
                    print(f"  Storage: {strategy['primary']} (RAG: {strategy['rag_enabled']})")
        
        # Demo 3: Interactive conversation with context
        print("\n\n3. Enhanced Conversation Demo")
        print("-"*40)
        
        # Simulate a conversation
        conversation = [
            ("user", "안녕하세요! 저는 이영희입니다."),
            ("user", "저는 백엔드 개발자이고 Java와 Spring을 사용해요."),
            ("user", "제가 누구라고 했죠?"),
            ("user", "제가 사용하는 기술 스택이 뭐였죠?"),
            ("user", "프론트엔드도 할 수 있나요?")
        ]
        
        for role, message in conversation:
            print(f"\n{role.upper()}: {message}")
            
            result = await client.process_prompt_enhanced(user_id, message, session_id)
            
            if result['success']:
                # Show processing details
                if result.get('processing_details'):
                    details = result['processing_details']
                    prompt_analysis = details.get('prompt_analysis', {})
                    context = details.get('context_found', {})
                    
                    print(f"  [Detected: {prompt_analysis.get('detected_type')}, " +
                          f"Importance: {prompt_analysis.get('importance')}, " +
                          f"Context: {context.get('total_context', 0)} items]")
                
                # Show response
                if result.get('response'):
                    print(f"ASSISTANT: {result['response']}")
        
        # Demo 4: Show stored memories
        print("\n\n4. Memory Retrieval Demo")
        print("-"*40)
        
        # Search for memories
        queries = [
            "이름",
            "기술",
            "개발자",
            "음식"
        ]
        
        for query in queries:
            print(f"\nSearching for: '{query}'")
            search_result = await client.session.call_tool(
                "search_user_memories",
                {
                    "user_id": user_id,
                    "query": query,
                    "limit": 3
                }
            )
            
            memories = json.loads(search_result.content).get('memories', [])
            if memories:
                for i, mem in enumerate(memories, 1):
                    print(f"  {i}. [{mem.get('type', 'unknown')}] {mem.get('content', '')[:60]}...")
                    if mem.get('keywords'):
                        print(f"     Keywords: {', '.join(mem['keywords'][:3])}")
            else:
                print("  No memories found")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.disconnect()

def main():
    """Run the enhanced memory demo"""
    print("Starting Enhanced Memory Client Demo...")
    print("Make sure the Memory Agent server is running on http://localhost:8094")
    print("")
    
    asyncio.run(demo_enhanced_features())

if __name__ == "__main__":
    main()