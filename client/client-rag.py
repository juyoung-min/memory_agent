# client-rag.py

import asyncio
import json
import logging
from typing import Optional
import argparse
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

from mcp import ClientSession
from mcp.client.sse import sse_client

class RAGMCPClient:
    def __init__(self, server_url: str):
        self.session: Optional[ClientSession] = None
        self.mcp_server_url = f"{server_url}/sse"

    async def connect(self):
        logging.info(f"Connecting to RAG-MCP Server at {self.mcp_server_url}...")
        try:
            logging.debug(f"Attempting to connect to SSE endpoint: {self.mcp_server_url}")
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

            if not isinstance(result.content, list) or not result.content:
                logging.warning(f"Received unexpected content format from tool '{tool_name}': {type(result.content)}. Content: {result.content}")
                if hasattr(result.content, 'text'):
                     try:
                        return json.loads(result.content.text)
                     except json.JSONDecodeError as e:
                        logging.error(f"Failed to decode JSON from unexpected tool response format: {e}. Content: {result.content.text}")
                        return {"status": "error", "message": f"Invalid JSON response from unexpected format: {e}"}
                return {"status": "error", "message": "Unexpected empty or non-list response content"}

            first_content_item = result.content[0]
            if not hasattr(first_content_item, 'text'):
                logging.warning(f"First content item from tool '{tool_name}' has no 'text' attribute. Type: {type(first_content_item)}. Content: {first_content_item}")
                return {"status": "error", "message": "First content item is not text-like"}

            try:
                return json.loads(first_content_item.text)
            except json.JSONDecodeError as e:
                logging.error(f"Failed to decode JSON from tool response: {e}. Content: {first_content_item.text}")
                if "Unknown tool" in first_content_item.text:
                    return {"status": "error", "message": f"Tool not found or server error: {first_content_item.text}"}
                return {"status": "error", "message": f"Invalid JSON response: {e}"}
        except Exception as e:
            logging.error(f"💥 Tool call error: {str(e)}", exc_info=True)
            return {"status": "error", "message": str(e)}

    async def cleanup(self):
        """Properly clean up the session and streams"""
        if self.session:
            await self._session_context.__aexit__(None, None, None)
        if self._streams_context:
            await self._streams_context.__aexit__(None, None, None)

async def main(server_url: str, action: str, content: Optional[str] = None, query: Optional[str] = None, namespace: str = "default"):
    logging.info(f"🎯 RAG-MCP Client")
    logging.info(f"   - Target Server: {server_url}")
    logging.info(f"   - Action: {action}")
    logging.info(f"   - Namespace: {namespace}")

    client = RAGMCPClient(server_url=server_url)

    try:
        if not await client.connect():
            print(json.dumps({"status": "error", "message": "Failed to connect to server"}, indent=2))
            return

        if action == "save":
            if not content:
                print("Content is required for save action")
                return
                
            logging.info(f"📝 Saving document...")
            result = await client.call_tool("rag_save_document", {
                "content": content,
                "namespace": namespace,
                "metadata": {
                    "source": "rag-client",
                    "timestamp": datetime.utcnow().isoformat()
                }
            })
            
        elif action == "search":
            if not query:
                print("Query is required for search action")
                return
                
            logging.info(f"🔍 Searching documents...")
            result = await client.call_tool("rag_search", {
                "query": query,
                "namespace": namespace,
                "limit": 5,
                "include_content": True
            })
            
        elif action == "answer":
            if not query:
                print("Question is required for answer action")
                return
                
            logging.info(f"🤔 Generating answer...")
            result = await client.call_tool("rag_generate_answer", {
                "question": query,
                "namespace": namespace,
                "search_limit": 5
            })
            
        else:
            print(f"Unknown action: {action}")
            return

        # Print result
        if result.get("success") or result.get("status") == "success":
            logging.info("Operation successful")
            print(f"\n📊 Result: {json.dumps(result, indent=2)}")
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
    if len(sys.argv) > 1 and not sys.argv[1].startswith('--'):
        server_url = sys.argv[1]
        sys.argv = [sys.argv[0]] + sys.argv[2:]
    else:
        server_url = "http://localhost:8093"

    parser = argparse.ArgumentParser(description='Run RAG MCP Client')
    parser.add_argument('--action', required=True, choices=['save', 'search', 'answer'],
                        help='Action to perform')
    parser.add_argument('--content', type=str,
                        help='Content for save action')
    parser.add_argument('--query', type=str,
                        help='Query for search/answer action')
    parser.add_argument('--namespace', type=str, default="default",
                        help='Namespace for operations (default: %(default)s)')

    args = parser.parse_args()

    # Add missing import
    from datetime import datetime

    asyncio.run(main(
        server_url=server_url,
        action=args.action,
        content=args.content,
        query=args.query,
        namespace=args.namespace
    ))