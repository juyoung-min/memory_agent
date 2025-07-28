#!/usr/bin/env python3
"""
Memory Operations Client for Memory Agent MCP
Focused on memory management: store, retrieve, delete
"""

import asyncio
import json
import logging
import argparse
from datetime import datetime
from typing import Optional, List, Dict, Any
from src.clients import InternalMCPClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MemoryClient:
    """Client for Memory Agent operations"""
    
    def __init__(self, server_url: str = "http://localhost:8094/sse"):
        self.client = InternalMCPClient(server_url, timeout=30)
        
    async def store_memory(
        self, 
        user_id: str, 
        content: str, 
        memory_type: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Store a new memory"""
        
        # Auto-generate session_id if not provided
        if not session_id:
            session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
        # Use store_memory_by_type for explicit type storage
        if memory_type:
            return await self.client.call_tool(
                "store_memory_by_type",
                {
                    "user_id": user_id,
                    "content": content,
                    "memory_type": memory_type,
                    "session_id": session_id
                }
            )
        else:
            # Use process_message for auto-classification
            return await self.client.call_tool(
                "process_message",
                {
                    "user_id": user_id,
                    "message": content,
                    "session_id": session_id
                }
            )
    
    async def retrieve_memories(
        self,
        user_id: str,
        query: str,
        memory_types: Optional[List[str]] = None,
        session_id: Optional[str] = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """Retrieve memories by search query"""
        
        # Use different tools based on what we're searching for
        if memory_types and "conversation" not in memory_types:
            # Search specific memory types
            return await self.client.call_tool(
                "search_user_memories",
                {
                    "user_id": user_id,
                    "query": query,
                    "session_id": session_id,
                    "memory_types": memory_types,
                    "limit": limit
                }
            )
        else:
            # Default to conversation history search
            return await self.client.call_tool(
                "get_conversation_history",
                {
                    "user_id": user_id,
                    "query": query,
                    "session_id": session_id,
                    "limit": limit
                }
            )
    
    async def delete_memory(self, user_id: str, memory_id: str) -> Dict[str, Any]:
        """Delete a specific memory"""
        return await self.client.call_tool(
            "delete_user_memory",
            {
                "user_id": user_id,
                "memory_id": memory_id
            }
        )
    
    async def get_stats(self, user_id: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Get memory statistics for user"""
        return await self.client.call_tool(
            "get_user_memory_stats",
            {
                "user_id": user_id,
                "session_id": session_id
            }
        )

async def main():
    parser = argparse.ArgumentParser(description="Memory Agent Operations Client")
    
    # Main action
    parser.add_argument(
        "action",
        choices=["store", "retrieve", "delete", "stats"],
        help="Action to perform"
    )
    
    # Common arguments
    parser.add_argument("--user-id", required=True, help="User ID")
    parser.add_argument("--session-id", help="Session ID (optional)")
    
    # Store arguments
    parser.add_argument("--content", help="Content to store (for store action)")
    parser.add_argument("--type", help="Memory type (fact, preference, identity, etc.)")
    
    # Retrieve arguments
    parser.add_argument("--query", help="Search query (for retrieve action)")
    parser.add_argument("--types", nargs="+", help="Memory types to search")
    parser.add_argument("--limit", type=int, default=10, help="Number of results")
    
    # Delete arguments
    parser.add_argument("--memory-id", help="Memory ID to delete")
    
    # Server URL
    parser.add_argument("--server-url", default="http://localhost:8094/sse", 
                       help="Memory Agent server URL")
    
    args = parser.parse_args()
    
    # Create client
    client = MemoryClient(args.server_url)
    
    try:
        # Execute action
        if args.action == "store":
            if not args.content:
                print("❌ Error: --content is required for store action")
                return
                
            print(f"📝 Storing memory for user: {args.user_id}")
            if args.type:
                print(f"   Type: {args.type}")
            print(f"   Content: {args.content[:100]}...")
            
            result = await client.store_memory(
                user_id=args.user_id,
                content=args.content,
                memory_type=args.type,
                session_id=args.session_id
            )
            
            if result.get("success"):
                print(f"✅ Memory stored successfully!")
                print(f"   ID: {result.get('memory_id')}")
                print(f"   Type: {result.get('memory_type')}")
                print(f"   Importance: {result.get('importance')}")
            else:
                print(f"❌ Failed to store memory: {result.get('error')}")
                
        elif args.action == "retrieve":
            if not args.query:
                print("❌ Error: --query is required for retrieve action")
                return
                
            print(f"🔍 Retrieving memories for user: {args.user_id}")
            print(f"   Query: {args.query}")
            if args.types:
                print(f"   Types: {args.types}")
                
            result = await client.retrieve_memories(
                user_id=args.user_id,
                query=args.query,
                memory_types=args.types,
                session_id=args.session_id,
                limit=args.limit
            )
            
            if result.get("success"):
                memories = result.get("conversations", []) or result.get("memories", [])
                print(f"\n✅ Found {len(memories)} memories:")
                
                for i, mem in enumerate(memories):
                    print(f"\n{i+1}. {mem.get('content', '')[:150]}...")
                    if 'similarity' in mem:
                        print(f"   Similarity: {mem['similarity']:.2f}")
                    if 'memory_type' in mem:
                        print(f"   Type: {mem['memory_type']}")
                    if 'timestamp' in mem:
                        print(f"   Time: {mem['timestamp']}")
            else:
                print(f"❌ Failed to retrieve memories: {result.get('error')}")
                
        elif args.action == "delete":
            if not args.memory_id:
                print("❌ Error: --memory-id is required for delete action")
                return
                
            print(f"🗑️ Deleting memory {args.memory_id} for user: {args.user_id}")
            
            result = await client.delete_memory(
                user_id=args.user_id,
                memory_id=args.memory_id
            )
            
            if result.get("success"):
                print("✅ Memory deleted successfully!")
            else:
                print(f"❌ Failed to delete memory: {result.get('error')}")
                
        elif args.action == "stats":
            print(f"📊 Getting memory statistics for user: {args.user_id}")
            
            result = await client.get_stats(
                user_id=args.user_id,
                session_id=args.session_id
            )
            
            if result.get("success"):
                stats = result.get("stats", {})
                print("\n✅ Memory Statistics:")
                print(f"   Total memories: {stats.get('total_memories', 0)}")
                print(f"   Average importance: {stats.get('average_importance', 0):.1f}")
                
                # Type distribution
                type_dist = stats.get("type_distribution", {})
                if type_dist:
                    print("\n   Memory types:")
                    for mem_type, count in type_dist.items():
                        print(f"     - {mem_type}: {count}")
                
                # Session distribution
                session_dist = stats.get("session_distribution", {})
                if session_dist:
                    print(f"\n   Sessions: {len(session_dist)}")
            else:
                print(f"❌ Failed to get stats: {result.get('error')}")
                
    except Exception as e:
        logger.error(f"Error: {e}")
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())