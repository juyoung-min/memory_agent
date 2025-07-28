import asyncio
import logging
import json
import os
import time
from typing import Any, Dict, Optional
import aiohttp
from mcp_instance import mcp

logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class InferenceServerProxy:
    def __init__(self):
        self.base_url = os.getenv("AI_INFERENCE_SERVER_URL", "http://192.168.1.209:31888")
        logging.info(f"🔧 Model Inference Manager URL (AIS): {self.base_url}")
        self._model_info_cache: Dict[str, Dict[str, Any]] = {}

    async def _fetch_model_list_from_ais(self) -> None: 
        models_endpoint = f"{self.base_url}/models"
        logging.info(f"Fetching model list from AIS: {models_endpoint}")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(models_endpoint, timeout=5) as response:
                    response.raise_for_status()
                    deploy_list = await response.json()

                    new_model_info_cache = {}
                    for item in deploy_list.get("deploys", []):
                        model_name = item.get("model_name")
                        if model_name: 
                            new_model_info_cache[model_name] = {
                                "id": item.get("id"),
                                "status": item.get("status"),
                                "app_type": item.get("app_type"),
                            }
                    self._model_info_cache = new_model_info_cache
                    logging.info("✅ Successfully fetched model info from AIS.")
        except Exception as e:
            logging.error(f"❌ Failed to fetch model list from AIS ({models_endpoint}): {e}", exc_info=True)
            self._model_info_cache = {}
            raise

    async def get_model_api_info(self, model_name: str) -> Optional[Dict[str, str]]:
        try:
            await self._fetch_model_list_from_ais()
        except Exception as e:
            logging.error(f"Failed to fetch model list for '{model_name}': {e}")
            return None

        model_info = self._model_info_cache.get(model_name)
        if not model_info:
            logging.error(f"Model info not found for model_name: '{model_name}' in AIS deployment list.")
            return None
            
        return model_info

    async def inference_phase(
        self,
        model_name: str,
        apipath: str,
        payload: Dict[str, Any]
    ) -> dict:
        model_info = await self.get_model_api_info(model_name)

        if not model_info or model_info.get("status") != "Ready" or not model_info.get("id"):
            status_msg = model_info.get("status", "Not Found") if model_info else "Not Found"
            error_message = f"Model '{model_name}' is not available for inference. Current status: {status_msg}."
            logging.warning(f"❌ {error_message}")
            
            return {"status": "error", "message": error_message}

        model_id = model_info["id"]
        model_api_base = f"api/{model_id}"

        if not apipath or not payload:
            return {"status": "error", "message": "apipath and payload must be provided."}

        inference_server_url = f"{self.base_url}/{model_api_base}/{apipath.lstrip('/')}"
        logging.info(f"Connecting to AIS inference endpoint: {inference_server_url}")

        try:
            headers = {"Content-Type": "application/json"}
            async with aiohttp.ClientSession() as session:
                async with session.post(inference_server_url, json=payload, headers=headers) as response:
                    response.raise_for_status()
                    result = await response.json()
                    
                    if not result:
                        logging.error(f"Received empty JSON response from AIS for {model_name}.")
                        return {"status": "error", "message": "Empty JSON response from AIS."}

                    logging.info(f"Received raw AIS inference result for {model_name}")
                    return result

        except Exception as e:
            logging.error(f"💥 Inference failed to AIS server: {e}", exc_info=True)
            return {"status": "error", "message": f"AIS server communication error: {str(e)}"}

proxy = InferenceServerProxy()

@mcp.tool(description="Inference AI model")
async def tool_inference_model(
    model_name: str,
    inference_payload: Dict[str, Any]
) -> dict:
    start_time = time.time()
    logging.info(f"🛠️ MCP Tool called: tool_inference_model(model={model_name})")

    apipath = inference_payload.get("apipath")
    payload = inference_payload.get("payload")

    if not apipath or not payload:
        logging.error("'inference_payload' must contain both 'apipath' and 'payload'.")
        return {"status": "error", "message": "Invalid inference_payload structure."}

    logging.info(f"🔮 Starting inference for model '{model_name}'...")
    inference_start = time.time()

    try:
        inference_result = await proxy.inference_phase(
            model_name, apipath, payload
        )
        inference_time = time.time() - inference_start

        if inference_result.get("status") == "error":
            return {
                "status": "error",
                "inference_time": inference_time,
                "message": inference_result.get("message", "AIS inference error."),
            }
        
        return {
            "status": "success",
            "inference_time": inference_time,
            **inference_result,
        }

    except Exception as e:
        logging.error(f"💥 Inference failed in tool: {e}", exc_info=True)
        return {
            "status": "error",
            "message": f"An unexpected error occurred: {str(e)}",
        }

@mcp.tool(description="Generate LLM completion")
async def generate_completion(
    prompt: str,
    model: str = "EXAONE-3.5-2.4B-Instruct",
    temperature: float = 0.7,
    max_tokens: int = 500
) -> dict:
    """Generate text completion using LLM"""
    result = await tool_inference_model(
        model_name=model,
        inference_payload={
            "apipath": "/v1/chat/completions",
            "payload": {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": False
            }
        }
    )
    
    # Extract text from the response for easier use
    if result.get("status") == "success":
        choices = result.get("choices", [])
        if choices:
            text = choices[0].get("message", {}).get("content", "")
            result["text"] = text
    
    return result

