import asyncio
import json
import os
import logging
from typing import Dict
import aiohttp
import argparse
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
from mcp import ClientSession
from mcp.client.sse import sse_client

class ModelMCPClient:
    def __init__(self, server_url: str):
        self.session: Optional[ClientSession] = None
        self.mcp_server_url = f"{server_url}/sse"
        self._streams_context = None
        self._session_context = None

    async def connect(self):
        logging.info(f"Connecting to MCP Server at {self.mcp_server_url}...")
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
            if not result.content or not isinstance(result.content, list) or not result.content[0].text:
                error_text = result.content[0].text if (result.content and isinstance(result.content, list) and result.content[0].text) else "No content in response"
                logging.error(f"Tool call failed or returned empty content. Raw response: {error_text}")
                try:
                    return json.loads(error_text)
                except (json.JSONDecodeError, TypeError):
                    return {"status": "error", "message": f"Tool execution failed: {error_text}"}
            try:
                return json.loads(result.content[0].text)
            except json.JSONDecodeError as e:
                logging.error(f"Failed to decode JSON from tool response: {e}. Content: {result.content[0].text}")
                return {"status": "error", "message": f"Invalid JSON response: {e}"}
        except Exception as e:
            logging.error(f"💥 Tool call error: {str(e)}", exc_info=True)
            return {"status": "error", "message": str(e)}

    async def cleanup(self):
        if self.session and self._session_context:
            await self._session_context.__aexit__(None, None, None)
        if self._streams_context:
            await self._streams_context.__aexit__(None, None, None)


async def main(server_url: str, model_name: str,apipath: str, payload_str: str):
    logging.info(f"🎯 MCP Model Client")
    logging.info(f"   - Target Server: {server_url}")
    logging.info(f"   - API Path: {apipath}")
    logging.info(f"   - Model Name to use : {model_name}")

    # 인자로 받은 json 문자열을 딕셔너리로 변환
    try: 
        payload = json.loads(payload_str)
    except json.JSONDecodeError as e:
        logging.error(f"❌ Failed to parse payload as JSON: {e}")
        return

    client = ModelMCPClient(server_url=server_url)
    try:
        if not await client.connect():
            print(json.dumps({"status": "error", "message": "Failed to connect to server"}, indent=2))
            return

        params = {
            "model_name": model_name,
            "inference_payload": {
                "apipath": apipath,
                "payload": payload # 변환된 딕셔너리 그대로 사용 
            }
        }
        logging.info(f"🚀 Requesting inference for {model_name}...")
        result = await client.call_tool("tool_inference_model", params)

        if result.get("status") == "success":
            logging.info(f"✅ Inference successful for {model_name}")
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            logging.error(f"❌ Inference failed for {model_name}")
            print(json.dumps(result, indent=2, ensure_ascii=False))

    except Exception as e:
        logging.error(f"❌ An unexpected error occurred: {str(e)}", exc_info=True)
    finally:
        logging.info("✨ Client cleanup initiated.")
        if 'client' in locals():
            await client.cleanup()
        logging.info("✨ Client cleanup completed.")

if __name__ == "__main__":
    if len(sys.argv) > 1 and not sys.argv[1].startswith('--'):
        server_url = sys.argv[1]
        sys.argv = [sys.argv[0]] + sys.argv[2:]
    else:
        server_url = "http://localhost:8091"

    parser = argparse.ArgumentParser(description='Run Generic Model MCP Client via Arguments')
    parser.add_argument('--model-name', required=True, help='The name of the model to use (e.g., tts)')
    parser.add_argument('--apipath', required=True, help='API endpoint path (e.g., /v1/completions)')
    parser.add_argument('--payload', required=True, help='Serialized JSON string containing the request payload')
    args = parser.parse_args()

    asyncio.run(main(
        server_url=server_url,
        model_name=args.model_name,
        apipath=args.apipath,
        payload_str=args.payload 
    ))