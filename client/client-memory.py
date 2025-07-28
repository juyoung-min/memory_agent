#!/usr/bin/env python3
"""
Memory Agent MCP Client
Test client for Memory Agent with type-specific storage and RAG integration
"""

import asyncio
import json
import logging
from typing import Optional, Dict, Any
import argparse
import sys
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

from mcp import ClientSession
from mcp.client.sse import sse_client

class MemoryMCPClient:
    def __init__(self, server_url: str):
        self.session: Optional[ClientSession] = None
        self.mcp_server_url = f"{server_url}/sse"

    async def connect(self):
        logging.info(f"Connecting to Memory Agent MCP Server at {self.mcp_server_url}...")
        try:
            self._streams_context = sse_client(url=self.mcp_server_url)
            streams = await self._streams_context.__aenter__()
            self._session_context = ClientSession(*streams)
            self.session = await self._session_context.__aenter__()
            await self.session.initialize()
            response = await self.session.list_tools()
            tool_names = [tool.name for tool in response.tools]
            logging.info(f"✅ Connection successful. Available tools: {tool_names}")
            return True
        except Exception as e:
            logging.error(f"💥 Failed to connect to server: {str(e)}", exc_info=True)
            return False

    async def call_tool(self, tool_name: str, params: dict) -> dict:
        try:
            result = await self.session.call_tool(tool_name, params)

            if not result.content:
                logging.warning(f"Received empty content from tool '{tool_name}'.")
                return {"status": "error", "message": "Empty response content from tool"}

            response_text = result.content[0].text
            
            try:
                return json.loads(response_text)
            except json.JSONDecodeError:
                logging.warning(f"Response is not JSON: {response_text}")
                return {"status": "success", "result": response_text}

        except Exception as e:
            logging.error(f"Error calling tool '{tool_name}': {str(e)}")
            return {"status": "error", "message": str(e)}

    async def cleanup(self):
        try:
            if hasattr(self, '_session_context'):
                await self._session_context.__aexit__(None, None, None)
            if hasattr(self, '_streams_context'):
                await self._streams_context.__aexit__(None, None, None)
        except Exception as e:
            logging.error(f"Cleanup error: {e}")


async def main(server_url: str, action: str, user_id: str, message: str = None, 
               session_id: str = None, memory_type: str = None):
    """
    Main client function
    """
    client = MemoryMCPClient(server_url)
    
    if not await client.connect():
        return
    
    try:
        result = {}  # Initialize result
        
        if action == "chat":
            if not message:
                print("Message is required for chat action")
                return
            
            # Use session_id or generate one
            if not session_id:
                session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            logging.info(f"💬 Processing prompt with automatic memory management...")
            
            result = await client.call_tool("process_user_prompt", {
                "user_id": user_id,
                "prompt": message,
                "session_id": session_id,
                "auto_store": True,
                "generate_response": True
            })
            
        elif action == "store":
            if not message:
                print("Message is required for store action")
                return
            
            # Use session_id or generate one
            if not session_id:
                session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            logging.info(f"💾 Storing message as memory...")
            
            if memory_type:
                # Store with specific type
                result = await client.call_tool("store_memory_by_type", {
                    "user_id": user_id,
                    "content": message,
                    "memory_type": memory_type,
                    "session_id": session_id
                })
            else:
                # Auto-classify and store
                result = await client.call_tool("process_message", {
                    "user_id": user_id,
                    "message": message,
                    "session_id": session_id
                })
            
        elif action == "history":
            if not message:
                message = ""  # Empty query gets recent history
            
            logging.info(f"📜 Retrieving conversation history...")
            
            result = await client.call_tool("get_conversation_history", {
                "user_id": user_id,
                "query": message,
                "session_id": session_id,
                "limit": 20
            })
            
        elif action == "search":
            if not message:
                print("Query is required for search action")
                return
            
            logging.info(f"🔍 Searching user memories...")
            
            result = await client.call_tool("search_user_memories", {
                "user_id": user_id,
                "query": message,
                "session_id": session_id,
                "limit": 10
            })
                
            
        elif action == "stats":
            logging.info(f"📊 Getting memory statistics...")
            
            result = await client.call_tool("get_user_memory_stats", {
                "user_id": user_id,
                "session_id": session_id
            })
            
        else:
            print(f"Unknown action: {action}")
            return

        # Print result
        if result.get("success"):
            logging.info("Operation successful")
            print(f"\n📊 Result:")
            
            if action == "chat":
                print(f"\n💬 Response: {result.get('response', '')}")
                
                # Show memory operations
                mem_ops = result.get('memory_operations', {})
                context = mem_ops.get('context_found', {})
                analysis = mem_ops.get('prompt_analysis', {})
                
                print(f"\n📊 Memory Operations:")
                print(f"  🔍 Context found: {context.get('conversations', 0)} conversations, {context.get('memories', 0)} memories")
                print(f"  🏷️ Detected type: {analysis.get('detected_type', 'unknown')}")
                print(f"  ⭐ Importance: {analysis.get('importance', 0):.1f}/10")
                print(f"  💾 Stored: {analysis.get('stored', False)}")
                
            elif action == "store":
                print(f"\n💾 Memory stored: {result.get('success', False)}")
                print(f"🏷️ Memory type: {result.get('memory_type', 'unknown')}")
                print(f"⭐ Importance: {result.get('importance', 0)}/10")
                print(f"📚 RAG stored: {result.get('rag_stored', False)}")
                if result.get('rag_namespace'):
                    print(f"📁 RAG namespace: {result.get('rag_namespace')}")
                print(f"💡 Storage strategy: {result.get('storage_strategy', 'unknown')}")
                
            elif action == "history" and "conversations" in result:
                print(f"\n📜 Found {result.get('count', 0)} conversations:")
                for i, conv in enumerate(result.get('conversations', [])[:5]):
                    print(f"\n{i+1}. {conv.get('content', '')[:100]}...")
                    print(f"   Similarity: {conv.get('similarity', 0):.3f}")
                    print(f"   Session: {conv.get('session_id', 'unknown')}")
                    print(f"   Time: {conv.get('timestamp', 'unknown')}")
                    
            elif action == "search" and "memories" in result:
                print(f"\n🔍 Found {result.get('count', 0)} memories:")
                for i, mem in enumerate(result.get('memories', [])[:5]):
                    print(f"\n{i+1}. [{mem.get('type', 'unknown')}] {mem.get('content', '')[:100]}...")
                    print(f"   Similarity: {mem.get('similarity', 0):.3f}")
                    print(f"   Importance: {mem.get('importance', 0)}/10")
                    
            else:
                print(json.dumps(result, indent=2))
        else:
            logging.error("Operation failed")
            print(json.dumps(result, indent=2))

    except Exception as e:
        logging.error(f"An unexpected error occurred: {str(e)}", exc_info=True)
        print(json.dumps({"status": "error", "message": f"An unexpected error occurred: {str(e)}"}, indent=2))

    finally:
        logging.info("Client cleanup initiated.")
        await client.cleanup()
        logging.info("Client cleanup completed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Memory Agent MCP Client')
    parser.add_argument('server_url', nargs='?', default='http://localhost:8094',
                        help='Memory Agent server URL (default: http://localhost:8094)')
    parser.add_argument('--action', required=True, choices=['chat', 'store', 'history', 'search', 'stats'],
                        help='Action to perform')
    parser.add_argument('--user-id', required=True,
                        help='User identifier')
    parser.add_argument('--message', type=str,
                        help='Message or query')
    parser.add_argument('--session-id', type=str,
                        help='Session identifier')
    parser.add_argument('--type', dest='memory_type',
                        choices=['fact', 'preference', 'identity', 'profession', 'skill',
                                'goal', 'hobby', 'experience', 'context', 'conversation'],
                        help='Memory type for store action')

    args = parser.parse_args()

    asyncio.run(main(
        server_url=args.server_url,
        action=args.action,
        user_id=args.user_id,
        message=args.message,
        session_id=args.session_id,
        memory_type=args.memory_type
    ))