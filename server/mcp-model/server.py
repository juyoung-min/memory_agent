from starlette.applications import Starlette
from mcp.server.sse import SseServerTransport
from starlette.requests import Request
from starlette.routing import Mount, Route
from starlette.responses import JSONResponse, Response
from mcp.server import Server
import uvicorn
import json

from mcp_instance import mcp

import importlib
import os

# import tools listed in tools/tool_list.txt
tool_dir = "tools"
tool_list_file = os.path.join(tool_dir, "tool_list.txt")

with open(tool_list_file, "r") as f:
    modules = [
        line.strip()
        for line in f
        if line.strip() and not line.strip().startswith("#")
    ]

for module_name in modules:
    importlib.import_module(f"{tool_dir}.{module_name}")
    print(f"Tool module : ", module_name)


def create_sse_app(mcp_server: Server, *, debug: bool = False) -> Starlette:
    """Create a Starlette application that can serve the provided mcp server with SSE."""
    # Create SSE transport with correct path
    sse = SseServerTransport("/messages/")
    
    async def handle_sse(request: Request):
        """Handle SSE connection"""
        print("SSE connection request received")
        async with sse.connect_sse(
            request.scope,
            request.receive,
            request._send,
        ) as (read_stream, write_stream):
            await mcp_server.run(
                read_stream,
                write_stream,
                mcp_server.create_initialization_options(),
            )
    
    async def handle_internal_tool(request: Request) -> JSONResponse:
        """Handle internal server-to-server tool calls."""
        try:
            # Parse request body
            body = await request.json()
            tool_name = body.get("tool_name")
            arguments = body.get("arguments", {})
            
            if not tool_name:
                return JSONResponse(
                    content={"error": "Missing required field: tool_name"},
                    status_code=400
                )
            
            # Get the tool from the mcp instance
            tool_func = None
            for tool in mcp._mcp_server._tools.values():
                if tool.name == tool_name:
                    tool_func = tool.func
                    break
            
            if not tool_func:
                return JSONResponse(
                    content={"error": f"Tool '{tool_name}' not found"},
                    status_code=404
                )
            
            # Call the tool with the provided arguments
            result = await tool_func(**arguments)
            
            return JSONResponse(content={"result": result})
            
        except json.JSONDecodeError:
            return JSONResponse(
                content={"error": "Invalid JSON in request body"},
                status_code=400
            )
        except TypeError as e:
            return JSONResponse(
                content={"error": f"Invalid arguments for tool '{tool_name}': {str(e)}"},
                status_code=400
            )
        except Exception as e:
            return JSONResponse(
                content={"error": f"Internal server error: {str(e)}"},
                status_code=500
            )
    
    # The SSE transport expects to handle messages via its own internal mechanism
    # We'll use Starlette's mount to properly delegate
    sse_app = Starlette(
        routes=[
            Route("/sse", endpoint=handle_sse, methods=["GET"]),
            Mount("/messages", app=sse),  # Mount the SSE transport as an ASGI app
            Route("/internal/tool", endpoint=handle_internal_tool, methods=["POST"]),
        ],
        debug=debug
    )
    
    return sse_app


if __name__ == "__main__":
    mcp_server = mcp._mcp_server
    print("start server.py")

    import argparse
    
    parser = argparse.ArgumentParser(description='Run MCP SSE-based server')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8000, help='Port to listen on')
    args = parser.parse_args()
    print("args")

    # Create SSE app using MCP's built-in method
    starlette_app = create_sse_app(mcp_server, debug=True)
    print(f"starlette_app: {starlette_app}")

    uvicorn.run(starlette_app, host=args.host, port=args.port)
