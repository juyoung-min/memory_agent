from .base_client import InternalMCPClient
import logging
from typing import Dict, Any, List
import asyncio
import json

logger = logging.getLogger(__name__)

class InternalModelClient(InternalMCPClient):
    """Internal client for server-to-server communication with Model-MCP"""
    
    async def generate_embedding(self, text: str, model_name: str = "bge-m3") -> Dict[str, Any]:
        """Generate embedding for text using Model-MCP"""
        
        logger.info(f"Generating embedding for text using model: {model_name}")
        
        response = await self.call_tool(
            "tool_inference_model",
            {
                "model_name": model_name,
                "inference_payload": {
                    "apipath": "/v1/embeddings",
                    "payload": {
                        "input": text,
                        "model": model_name
                    }
                }
            }
        )
        
        if response.get("status") == "error":
            logger.error(f"Failed to generate embedding: {response.get('message')}")
            return response
            
        # Extract embedding from response
        # For bge-m3 model, the response format is {"data": [{"embedding": [...]}]}
        embedding = None
        if response.get("data") and len(response["data"]) > 0:
            embedding = response["data"][0].get("embedding")
        else:
            # Fallback for other formats
            embedding = response.get("embedding") or response.get("result", {}).get("embedding")
        
        if not embedding:
            logger.error(f"No embedding found in model response: {response}")
            return {
                "success": False,
                "error": "No embedding in response",
                "error_type": "EmbeddingError"
            }
            
        return {
            "success": True,
            "embedding": embedding,
            "model": model_name
        }
    
    async def generate_response(self, prompt: str, model_name: str = "EXAONE-3.5-2.4B-Instruct", max_tokens: int = 1024) -> Dict[str, Any]:
        """Generate LLM response using Model-MCP"""
        
        logger.info(f"Generating response using model: {model_name}")
        
        response = await self.call_tool(
            "tool_inference_model",
            {
                "model_name": model_name,
                "inference_payload": {
                    "apipath": "/v1/chat/completions",
                    "payload": {
                        "model": model_name,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": max_tokens,
                        "stream": False
                    }
                }
            }
        )
        
        # The response is already parsed JSON from base_client
        logger.info(f"Model response type: {type(response)}")
        logger.info(f"Model response keys: {list(response.keys()) if isinstance(response, dict) else 'Not a dict'}")
        
        # Log the full response structure for debugging
        if isinstance(response, dict):
            logger.info(f"Model response status: {response.get('status')}")
            if response.get("choices"):
                logger.info(f"Found choices in response")
                
        return response
    
    async def batch_generate_embeddings(self, texts: List[str], model_name: str = "bge-m3") -> Dict[str, Any]:
        """Generate embeddings for multiple texts"""
        
        logger.info(f"Generating embeddings for {len(texts)} texts")
        
        embeddings = []
        errors = []
        
        # Process in parallel with limited concurrency
        semaphore = asyncio.Semaphore(5)  # Limit to 5 concurrent requests
        
        async def generate_with_semaphore(text, index):
            async with semaphore:
                result = await self.generate_embedding(text, model_name)
                return index, result
        
        tasks = [generate_with_semaphore(text, i) for i, text in enumerate(texts)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Sort results by original index
        sorted_results = sorted(results, key=lambda x: x[0] if isinstance(x, tuple) else -1)
        
        for idx, result in sorted_results:
            if isinstance(result, Exception):
                errors.append({"index": idx, "error": str(result)})
                embeddings.append(None)
            elif result.get("success"):
                embeddings.append(result.get("embedding"))
            else:
                errors.append({"index": idx, "error": result.get("error")})
                embeddings.append(None)
        
        return {
            "success": len(errors) == 0,
            "embeddings": embeddings,
            "errors": errors if errors else None,
            "total": len(texts),
            "successful": len([e for e in embeddings if e is not None])
        }