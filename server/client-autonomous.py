"""
Autonomous Memory Agent Client
The Memory Agent autonomously decides what actions to take based on user prompts
"""

import asyncio
import argparse
import json
from datetime import datetime
from mcp import ClientSession, SSEServerTransport
from httpx import AsyncClient, Limits
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AutonomousMemoryClient:
    def __init__(self, base_url="http://localhost:8094/sse"):
        self.base_url = base_url
        self.session = None
        self.http_client = None
        
    async def connect(self):
        """Connect to the Memory Agent MCP server"""
        logger.info(f"Connecting to Memory Agent at {self.base_url}...")
        
        self.http_client = AsyncClient(
            timeout=30.0,
            limits=Limits(max_keepalive_connections=1, max_connections=5),
        )
        
        sse_transport = SSEServerTransport(self.http_client, self.base_url)
        self.session = ClientSession(sse_transport)
        
        await self.session.initialize()
        logger.info("✅ Connected to Memory Agent")
        
        return True
    
    async def disconnect(self):
        """Disconnect from the server"""
        if self.http_client:
            await self.http_client.aclose()
        logger.info("Disconnected from Memory Agent")
    
    async def send_prompt(self, user_id: str, prompt: str, session_id: str = None):
        """
        Send a prompt to the Memory Agent and let it decide what to do
        The agent will autonomously:
        - Analyze the prompt
        - Retrieve relevant context
        - Store the interaction
        - Generate a response
        """
        if not session_id:
            session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        logger.info(f"Sending prompt to Memory Agent for autonomous processing...")
        
        # Use process_user_prompt which handles everything automatically
        result = await self.session.call_tool(
            "process_user_prompt",
            {
                "user_id": user_id,
                "prompt": prompt,
                "session_id": session_id,
                "auto_store": True,      # Let agent decide what to store
                "generate_response": True # Let agent generate response
            }
        )
        
        return json.loads(result.content)

async def interactive_mode(client: AutonomousMemoryClient, user_id: str):
    """Interactive conversation mode"""
    session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    print("\n=== Autonomous Memory Agent ===")
    print("The agent will automatically manage your conversation memory.")
    print("Type 'exit' to quit, 'stats' to see memory statistics.\n")
    
    while True:
        try:
            # Get user input
            prompt = input(f"\n[{user_id}] You: ").strip()
            
            if prompt.lower() == 'exit':
                break
            elif prompt.lower() == 'stats':
                # Get memory statistics
                stats_result = await client.session.call_tool(
                    "get_user_memory_stats",
                    {"user_id": user_id, "session_id": session_id}
                )
                stats = json.loads(stats_result.content)
                if stats.get("success"):
                    print("\n📊 Memory Statistics:")
                    print(json.dumps(stats["stats"], indent=2))
                continue
            elif not prompt:
                continue
            
            # Send prompt and let agent handle everything
            result = await client.send_prompt(user_id, prompt, session_id)
            
            if result.get("success"):
                # Show the response
                response = result.get("response", "")
                if response:
                    print(f"\n[Agent] Response: {response}")
                
                # Show what the agent did (optional debug info)
                if result.get("memory_operations"):
                    ops = result["memory_operations"]
                    logger.debug(f"Context found: {ops.get('context_found', {})}")
                    logger.debug(f"Prompt analysis: {ops.get('prompt_analysis', {})}")
            else:
                print(f"\n❌ Error: {result.get('error', 'Unknown error')}")
                
        except KeyboardInterrupt:
            print("\n\nExiting...")
            break
        except Exception as e:
            logger.error(f"Error: {e}")

async def single_prompt_mode(client: AutonomousMemoryClient, user_id: str, prompt: str):
    """Send a single prompt and show results"""
    session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    result = await client.send_prompt(user_id, prompt, session_id)
    
    if result.get("success"):
        print("\n=== Memory Agent Response ===")
        
        # Show the response
        response = result.get("response", "")
        if response:
            print(f"\nResponse: {response}")
        
        # Show memory operations performed
        if result.get("memory_operations"):
            ops = result["memory_operations"]
            print("\n📊 Memory Operations:")
            
            # Context retrieval
            context = ops.get("context_found", {})
            if context:
                print(f"  - Found {context.get('conversations', 0)} conversations")
                print(f"  - Found {context.get('memories', 0)} related memories")
            
            # Prompt analysis
            analysis = ops.get("prompt_analysis", {})
            if analysis:
                print(f"  - Detected type: {analysis.get('detected_type', 'unknown')}")
                print(f"  - Importance: {analysis.get('importance', 0)}/10")
                print(f"  - Stored: {'Yes' if analysis.get('stored') else 'No'}")
            
            # Storage details
            storage = ops.get("storage_details")
            if storage and storage.get("memory_id"):
                print(f"  - Memory ID: {storage['memory_id']}")
                print(f"  - Storage strategy: {storage.get('storage_strategy', 'default')}")
    else:
        print(f"\n❌ Error: {result.get('error', 'Unknown error')}")

async def main():
    parser = argparse.ArgumentParser(description="Autonomous Memory Agent Client")
    parser.add_argument("--user-id", required=True, help="User identifier")
    parser.add_argument("--prompt", help="Single prompt to send (interactive mode if not provided)")
    parser.add_argument("--url", default="http://localhost:8094/sse", help="Memory Agent URL")
    
    args = parser.parse_args()
    
    client = AutonomousMemoryClient(args.url)
    
    try:
        # Connect to Memory Agent
        await client.connect()
        
        if args.prompt:
            # Single prompt mode
            await single_prompt_mode(client, args.user_id, args.prompt)
        else:
            # Interactive mode
            await interactive_mode(client, args.user_id)
            
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())