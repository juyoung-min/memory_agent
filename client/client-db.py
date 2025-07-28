import asyncio
import json
import os
import sys
from typing import Optional
from contextlib import AsyncExitStack

from mcp import ClientSession
from mcp.client.sse import sse_client

from dotenv import load_dotenv

load_dotenv()  # load environment variables from .env

class MCPClient:
    def __init__(self):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.available_tools = []

    async def connect_to_sse_server(self, server_url: str):
        """Connect to an MCP server running with SSE transport"""
        # Store the context managers so they stay alive
        self._streams_context = sse_client(url=server_url)
        streams = await self._streams_context.__aenter__()

        self._session_context = ClientSession(*streams)
        self.session: ClientSession = await self._session_context.__aenter__()

        # Initialize
        await self.session.initialize()

        # List available tools to verify connection
        print("🔗 Initialized DB-MCP SSE client...")
        print("📋 Listing tools...")
        response = await self.session.list_tools()
        tools = response.tools
        print("\\n✅ Connected to DB-MCP server with tools:", [tool.name for tool in tools])

        self.available_tools = [{ 
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.inputSchema
        } for tool in tools]

        for tool in self.available_tools: 
            print(f"\\n🔧 Tool name: {tool['name']}")
            print(f"📄 Description: {tool['description']}")
            print(f"📥 Input schema:\\n{json.dumps(tool['input_schema'], indent=2)}")

    async def cleanup(self):
        """Properly clean up the session and streams"""
        if self._session_context:
            await self._session_context.__aexit__(None, None, None)
        if self._streams_context:
            await self._streams_context.__aexit__(None, None, None)

    async def call_loop(self):
        print("\\n🚀 DB-MCP Client Started!")

        while True:
            print("\\n🔧 사용 가능한 Tool 목록:")
            for idx, tool in enumerate(self.available_tools):
                print(f"{idx}: {tool['name']}")

            print("L: 최근 메모리 목록 보기")
            print("8: 메모리 데모 실행")
            print("9: 종료")
            choice = input("실행할 Tool 번호를 입력하세요: ").strip()

            if choice == "9":
                print("👋 종료합니다.")
                break

            if choice == "8":
                await self.run_memory_demo()
                continue
            
            if choice.upper() == "L":
                await self.list_recent_memories()
                continue

            if not choice.isdigit() or int(choice) >= len(self.available_tools):
                print("⚠️ 올바르지 않은 번호입니다. 다시 입력하세요.")
                continue

            tool_idx = int(choice)
            tool_name = self.available_tools[tool_idx]["name"]
            
            print(f"Selected tool: {tool_name} (index {tool_idx})")

            # Memory tool input examples
            tool_input = {}
            should_continue = False
            
            
            if tool_name == "db_insert_memory":
                tool_input = {
                    "request": {
                        "content": "사용자는 다크 모드 인터페이스를 선호합니다",
                        "embedding": [0.1 + i * 0.001 for i in range(1536)],  # 1536차원 벡터
                        "namespace": "user_123",
                        "memory_type": "preference",
                        "importance": 0.8,
                        "metadata": {"ui_theme": "dark", "language": "korean"},
                        "tags": ["ui", "preference", "theme"]
                    }
                }
            elif tool_name == "db_search_memories":
                tool_input = {
                    "request": {
                        "query_vector": [0.1 + i * 0.001 for i in range(1536)],  # 1536차원 쿼리 벡터
                        "namespace": "user_123", 
                        "memory_type": "preference",
                        "limit": 5,
                        "similarity_threshold": 0.5
                    }
                }
            elif tool_name == "db_list_memories":
                namespace = input("네임스페이스를 입력하세요 (Enter로 user_123): ").strip()
                if not namespace:
                    namespace = "user_123"
                tool_input = {
                    "request": {
                        "namespace": namespace,
                        "limit": 10
                    }
                }
            elif tool_name == "update_memory":
                # 먼저 메모리 ID를 입력받거나 하드코딩
                print("힌트: 메모리 ID는 UUID 형식입니다 (예: 66b98183-911d-4acb-9399-a913aaf8902e)")
                memory_id = input("업데이트할 메모리 ID를 입력하세요 (또는 Enter로 건너뛰기): ").strip()
                if memory_id:
                    tool_input = {
                        "request": {
                            "memory_id": memory_id,
                            "importance": 0.9,
                            "metadata": {"ui_theme": "dark", "updated": True}
                        }
                    }
                else:
                    print("메모리 ID가 필요합니다.")
                    should_continue = True
            elif tool_name == "get_memory":
                print("힌트: 메모리 ID는 UUID 형식입니다 (예: 66b98183-911d-4acb-9399-a913aaf8902e)")
                print("힌트: save_memory를 실행하면 새로운 메모리 ID를 얻을 수 있습니다")
                memory_id = input("조회할 메모리 ID를 입력하세요 (또는 Enter로 건너뛰기): ").strip()
                if memory_id:
                    tool_input = {"request": {"memory_id": memory_id}}
                else:
                    print("메모리 ID가 필요합니다.")
                    should_continue = True
            elif tool_name == "db_delete_memory":
                print("힌트: 메모리 ID는 UUID 형식입니다 (예: 66b98183-911d-4acb-9399-a913aaf8902e)")
                memory_id = input("삭제할 메모리 ID를 입력하세요 (또는 Enter로 건너뛰기): ").strip()
                if memory_id:
                    tool_input = {"request": {"id": memory_id}}  # Note: parameter name is 'id', not 'memory_id'
                else:
                    print("메모리 ID가 필요합니다.")
                    should_continue = True
            elif tool_name == "get_memory_stats":
                namespace = input("네임스페이스를 입력하세요 (Enter로 전체): ").strip()
                # Check if tool expects kwargs parameter
                input_schema = self.available_tools[tool_idx].get("input_schema", {})
                if "kwargs" in input_schema.get("properties", {}):
                    tool_input = {"kwargs": json.dumps({"namespace": namespace} if namespace else {})}
                else:
                    tool_input = {"request": {"namespace": namespace}} if namespace else {"request": {}}
            elif tool_name == "get_database_health":
                # Check if tool expects kwargs parameter
                input_schema = self.available_tools[tool_idx].get("input_schema", {})
                if "kwargs" in input_schema.get("properties", {}):
                    tool_input = {"kwargs": "{}"}
                else:
                    tool_input = {"request": {}}
            elif tool_name == "save_long_term_memory":
                tool_input = {
                    "request": {
                        "content": "장기 메모리 테스트 - 사용자는 다크 모드를 선호합니다",
                        "embedding": [0.1] * 1536,  # 1536차원 더미 벡터
                        "namespace": "user_123",
                        "memory_type": "preference",
                        "importance": 0.9,
                        "metadata": {"ui_theme": "dark", "source": "long_term_memory"},
                        "tags": ["ui", "preference", "long-term"]
                    }
                }
            elif tool_name == "search_long_term_memory":
                tool_input = {
                    "request": {
                        "query_embedding": [0.1] * 1536,  # 1536차원 쿼리 벡터
                        "limit": 5,
                        "similarity_threshold": 0.7
                    }
                }
            elif tool_name == "get_long_term_memory_info":
                # Check if tool expects kwargs parameter
                input_schema = self.available_tools[tool_idx].get("input_schema", {})
                if "kwargs" in input_schema.get("properties", {}):
                    tool_input = {"kwargs": "{}"}
                else:
                    tool_input = {"request": {}}
            elif tool_name == "find_relevant_memory":
                context = input("검색할 컨텍스트나 쿼리를 입력하세요: ").strip()
                if context:
                    tool_input = {
                        "request": {
                            "context": context,
                            "namespace": "user_123",
                            "limit": 5
                        }
                    }
                else:
                    print("컨텍스트나 쿼리가 필요합니다.")
                    should_continue = True
            elif tool_name == "smart_memory_update":
                content = input("저장하거나 업데이트할 내용을 입력하세요: ").strip()
                if content:
                    tool_input = {
                        "request": {
                            "content": content,
                            "namespace": "user_123",
                            "memory_type": "general",
                            "importance": 0.7,
                            "embedding": [0.1] * 1536
                        }
                    }
                else:
                    print("내용이 필요합니다.")
                    should_continue = True
            elif tool_name == "auto_cleanup_memories":
                tool_input = {
                    "request": {
                        "namespace": "user_123",
                        "max_memories": 100,
                        "keep_recent_days": 30,
                        "min_importance": 0.3
                    }
                }
            elif tool_name == "memory_insights":
                namespace = input("분석할 네임스페이스를 입력하세요 (Enter로 기본값): ").strip()
                tool_input = {
                    "request": {
                        "namespace": namespace or "user_123"
                    }
                }
            else:
                # Unknown tool - show warning
                print(f"⚠️ Warning: No predefined input for tool '{tool_name}'")
                print("Using empty input. This may cause validation errors.")

            # Check if we should skip this iteration
            if should_continue:
                continue

            # Add new simplified DB tools
            if tool_name == "db_insert_memory" and not tool_input:
                tool_input = {
                    "request": {
                        "content": "사용자는 다크 모드 인터페이스를 선호합니다",
                        "embedding": [0.1] * 1536,  # 1536차원 더미 벡터
                        "namespace": "user_123",
                        "memory_type": "preference",
                        "importance": 0.8,
                        "metadata": {"ui_theme": "dark", "language": "korean"},
                        "tags": ["ui", "preference", "theme"]
                    }
                }
            
            # Ensure tool_input is properly formatted for SSE transport
            if not tool_input:
                # Check tool input schema to determine correct format
                input_schema = self.available_tools[tool_idx].get("input_schema", {})
                if "kwargs" in input_schema.get("properties", {}):
                    tool_input = {"kwargs": "{}"}
                else:
                    tool_input = {"request": {}}

            print(f"\\n🚀 실행 중: {tool_name}")
            print(f"입력값: {json.dumps(tool_input, indent=2, ensure_ascii=False)}")

            try:
                tool_result = await self.session.call_tool(
                    name=tool_name,
                    arguments=tool_input
                )
                # class 'mcp.types.CallToolResult' 리턴
                print("\\033[93m", "📎 meta : ", tool_result.meta, "\\033[0m")
                print("\\033[93m", "📎 error: ", tool_result.isError, "\\033[0m")
                for content in tool_result.content:
                    print("📝 Content type:", content.type)
                    if not content.text:
                        print("⚠️  Warning: Empty response from server")
                        continue
                    try:
                        # JSON 파싱 시도
                        result_data = json.loads(content.text)
                        print("📝 Content (parsed):", json.dumps(result_data, indent=2, ensure_ascii=False))
                    except json.JSONDecodeError as e:
                        # JSON이 아닌 경우 그대로 출력
                        print(f"⚠️  JSON parse error: {e}")
                        print("📝 Raw content:", repr(content.text))
                    except Exception as e:
                        print(f"❌ Unexpected error: {e}")
                        print("📝 Raw content:", repr(content.text))

            except Exception as e:
                print(f"❌ Tool 실행 중 오류: {e}")

    async def run_memory_demo(self):
        """메모리 작업 데모 실행"""
        print("\\n🎯 메모리 데모를 시작합니다...")
        
        # 1. 메모리 저장
        print("\\n1️⃣ 메모리 저장...")
        save_input = {
            "request": {
                "content": "사용자는 다크 모드와 한국어를 선호합니다",
                "embedding": [0.1] * 1536,
                "namespace": "demo_user",
                "memory_type": "preference",
                "importance": 0.8,
                "metadata": {"ui_theme": "dark", "language": "ko"},
                "tags": ["ui", "preference", "demo"]
            }
        }
        
        try:
            save_result = await self.session.call_tool(name="db_insert_memory", arguments=save_input)
            save_data = json.loads(save_result.content[0].text)
            print(f"✅ 저장 결과: {save_data}")
            
            if save_data.get('success'):
                memory_id = save_data.get('id')
                
                # 2. 메모리 검색
                print("\\n2️⃣ 메모리 검색...")
                search_input = {
                    "request": {
                        "query_vector": [0.1] * 1536,
                        "namespace": "demo_user",
                        "limit": 5
                    }
                }
                
                search_result = await self.session.call_tool(name="db_search_memories", arguments=search_input)
                
                # Debug: Check what we're getting
                if search_result.isError:
                    print(f"❌ 검색 오류: {search_result.content[0].text if search_result.content else 'No error message'}")
                elif not search_result.content:
                    print("❌ 검색 결과가 비어있습니다")
                else:
                    try:
                        search_data = json.loads(search_result.content[0].text)
                        print(f"✅ 검색 결과: {len(search_data.get('results', []))}개 메모리 발견")
                    except json.JSONDecodeError as e:
                        print(f"❌ JSON 파싱 오류: {e}")
                        print(f"   원본 응답: '{search_result.content[0].text}'")
                
                # 3. 메모리 목록 조회
                print("\\n3️⃣ 메모리 목록 조회...")
                list_input = {
                    "request": {
                        "namespace": "demo_user",
                        "limit": 10
                    }
                }
                list_result = await self.session.call_tool(name="db_list_memories", arguments=list_input)
                list_data = json.loads(list_result.content[0].text)
                if list_data.get('success'):
                    print(f"✅ 목록 조회: {len(list_data.get('results', []))}개 메모리")
                    pagination = list_data.get('pagination', {})
                    print(f"   전체: {pagination.get('total', 0)}개, 페이지: {pagination.get('offset', 0)}/{pagination.get('limit', 10)}")
                
                # 4. 메모리 삭제 (정리)
                print("\\n4️⃣ 메모리 정리...")
                delete_result = await self.session.call_tool(name="db_delete_memory", arguments={"request": {"id": memory_id}})
                delete_data = json.loads(delete_result.content[0].text)
                print(f"✅ 삭제 결과: {delete_data}")
                
        except Exception as e:
            print(f"❌ 데모 실행 중 오류: {e}")
        
        print("\\n🎉 메모리 데모가 완료되었습니다!")
    
    async def list_recent_memories(self):
        """최근 메모리 목록을 표시"""
        print("\\n📋 최근 메모리 목록을 가져옵니다...")
        
        # Use db_list_memories tool (new simplified tool)
        list_tool = next((t for t in self.available_tools if t["name"] == "db_list_memories"), None)
        
        if not list_tool:
            print("❌ db_list_memories 도구를 찾을 수 없습니다.")
            print("💡 사용 가능한 도구들:", [t["name"] for t in self.available_tools])
            return
        
        try:
            # Call the tool with optional namespace
            list_args = {"request": {"limit": 10, "order_by": "created_at", "order_desc": True}}
            list_result = await self.session.call_tool(name="db_list_memories", arguments=list_args)
            
            if list_result.isError:
                print(f"❌ 오류: {list_result.content[0].text}")
                return
                
            list_data = json.loads(list_result.content[0].text)
            
            if list_data.get('success') and list_data.get('results'):
                # For new db_list_memories tool
                results = list_data.get('results', [])
                print(f"\\n✅ 최근 {len(results)}개의 메모리:")
                print("-" * 80)
                
                for mem in results:
                    print(f"ID: {mem['id']}")
                    print(f"내용: {mem['content'][:100]}...")  # Truncate long content
                    print(f"네임스페이스: {mem['namespace']}")
                    print(f"타입: {mem['type']}")
                    print(f"중요도: {mem['importance']}")
                    print(f"생성일: {mem['created_at']}")
                    if mem.get('tags'):
                        print(f"태그: {', '.join(mem['tags'])}")
                    print("-" * 80)
            else:
                print("📭 저장된 메모리가 없습니다.")
                
        except Exception as e:
            print(f"❌ 메모리 목록 조회 중 오류: {e}")

async def main():
    if len(sys.argv) < 2:
        print("Usage: python client-db.py <URL of DB-MCP SSE server (i.e. http://localhost:8085/sse)>")
        print("Example: python client-db.py http://localhost:8085/sse")
        sys.exit(1)

    client = MCPClient()
    try:
        await client.connect_to_sse_server(server_url=sys.argv[1])
        await client.call_loop()
    finally:
        await client.cleanup()

if __name__ == "__main__":
    asyncio.run(main())