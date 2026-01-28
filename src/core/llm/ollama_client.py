import httpx
import json
from src.core.config import settings

class OllamaClient:
    def __init__(self, base_url: str = settings.OLLAMA_BASE_URL, model: str = settings.OLLAMA_MODEL):
        self.base_url = base_url
        self.model = model
        self.client = httpx.AsyncClient(base_url=self.base_url, timeout=60.0)

    async def generate(self, prompt: str, system: str = None, options: dict = None) -> str:
        url = "/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False
        }
        if system:
            payload["system"] = system
        if options:
            payload["options"] = options

        try:
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("response", "")
        except httpx.HTTPError as e:
            print(f"Ollama generation error: {e}")
            raise

    async def chat(self, messages: list[dict], options: dict = None) -> dict:
        """
        messages: list of dicts with 'role' and 'content' keys.
        """
        url = "/api/chat"
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False
        }
        if options:
            payload["options"] = options

        try:
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("message", {})
        except httpx.HTTPError as e:
            print(f"Ollama chat error: {e}")
            raise

    async def close(self):
        await self.client.aclose()

ollama_client = OllamaClient()

async def get_llm():
    return ollama_client
