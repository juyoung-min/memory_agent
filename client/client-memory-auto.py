#!/usr/bin/env python3
"""
Autonomous Memory Agent Client
The Memory Agent autonomously decides what actions to take based on user prompts
No need to specify actions - just send your message!
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

class AutonomousMemoryClient:
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
            logging.info(f"✅ Connection successful. Memory Agent is ready!")
            logging.debug(f"Available tools: {tool_names}")
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

    async def process_message(self, user_id: str, message: str, session_id: str = None):
        """
        Send message to Memory Agent which will autonomously:
        1. Analyze the message to understand intent
        2. Retrieve relevant context from memory
        3. Store the interaction appropriately
        4. Generate an intelligent response
        """
        if not session_id:
            session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        logging.info(f"🤖 Memory Agent is processing your message...")
        
        # Use process_user_prompt which handles everything autonomously
        result = await self.call_tool("process_user_prompt", {
            "user_id": user_id,
            "prompt": message,
            "session_id": session_id,
            "auto_store": True,      # Agent decides what to store
            "generate_response": True # Agent generates response
        })
        
        return result

    async def cleanup(self):
        try:
            logging.info("Client cleanup initiated.")
            if hasattr(self, '_session_context'):
                await self._session_context.__aexit__(None, None, None)
            if hasattr(self, '_streams_context'):
                await self._streams_context.__aexit__(None, None, None)
            logging.info("Client cleanup completed.")
        except Exception as e:
            logging.error(f"Cleanup error: {e}")


async def main():
    """
    Main client function - no action required, just message!
    """
    parser = argparse.ArgumentParser(
        description="Autonomous Memory Agent Client - Just send your message!"
    )
    parser.add_argument("--server-url", type=str, default="http://localhost:8094",
                        help="Memory Agent server URL")
    parser.add_argument("--user-id", type=str, required=True,
                        help="User identifier")
    parser.add_argument("--message", type=str, 
                        help="Your message (interactive mode if not provided)")
    parser.add_argument("--session-id", type=str,
                        help="Session ID (auto-generated if not provided)")
    
    args = parser.parse_args()
    
    client = AutonomousMemoryClient(args.server_url)
    
    if not await client.connect():
        return
    
    try:
        if args.message:
            # Single message mode
            result = await client.process_message(
                args.user_id, 
                args.message, 
                args.session_id
            )
            
            if result.get("success"):
                print("\n" + "="*60)
                print("🤖 Memory Agent Response")
                print("="*60)
                
                # Show the response
                if result.get("response"):
                    print(f"\n💬 Response: {result['response']}")
                
                # Show what the agent did
                if result.get("memory_operations"):
                    ops = result["memory_operations"]
                    print("\n📊 What the Memory Agent did:")
                    
                    # Context found
                    context = ops.get("context_found", {})
                    if context.get("conversations", 0) > 0 or context.get("memories", 0) > 0:
                        print(f"  ✓ Retrieved context: {context.get('conversations', 0)} conversations, {context.get('memories', 0)} memories")
                    
                    # Analysis
                    analysis = ops.get("prompt_analysis", {})
                    if analysis:
                        print(f"  ✓ Detected type: {analysis.get('detected_type', 'unknown')}")
                        print(f"  ✓ Importance: {analysis.get('importance', 0)}/10")
                        if analysis.get("stored"):
                            print(f"  ✓ Stored in memory")
                    
                    # Storage details
                    storage = ops.get("storage_details")
                    if storage and storage.get("memory_id"):
                        print(f"  ✓ Memory ID: {storage['memory_id']}")
            else:
                print(f"\n❌ Error: {result.get('error', 'Unknown error')}")
        
        else:
            # Interactive mode
            session_id = args.session_id or f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            print("\n" + "="*60)
            print("🤖 Autonomous Memory Agent - Interactive Mode")
            print("="*60)
            print("Just type your messages and the Memory Agent will handle everything!")
            print("Commands: 'exit' to quit, 'stats' for memory statistics")
            print("-"*60)
            
            while True:
                try:
                    message = input(f"\n[{args.user_id}] You: ").strip()
                    
                    if message.lower() == 'exit':
                        break
                    elif message.lower() == 'stats':
                        stats_result = await client.call_tool("get_user_memory_stats", {
                            "user_id": args.user_id,
                            "session_id": session_id
                        })
                        if stats_result.get("success"):
                            print("\n📊 Your Memory Statistics:")
                            stats = stats_result.get("stats", {})
                            print(f"  Total memories: {stats.get('total_memories', 0)}")
                            print(f"  Memory types: {stats.get('type_distribution', {})}")
                            print(f"  Sessions: {stats.get('session_count', 0)}")
                        continue
                    elif not message:
                        continue
                    
                    # Process message
                    result = await client.process_message(
                        args.user_id,
                        message,
                        session_id
                    )
                    
                    if result.get("success"):
                        if result.get("response"):
                            print(f"\n[Agent] {result['response']}")
                        else:
                            print("\n[Agent] ✓ Processed and stored")
                    else:
                        print(f"\n❌ Error: {result.get('error', 'Unknown error')}")
                        
                except KeyboardInterrupt:
                    print("\n\nExiting...")
                    break
                except Exception as e:
                    logging.error(f"Error: {e}")
                    
    except Exception as e:
        logging.error(f"Error: {e}", exc_info=True)
    finally:
        await client.cleanup()


if __name__ == "__main__":
    asyncio.run(main())