import os
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

class OpenRouterClient:
    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY", "dummy-key")
        self.client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=self.api_key,
        )
        self.model = "stepfun/step-3.5-flash:free"

    async def generate_response(self, messages: list, tools: Optional[List[Dict[str, Any]]] = None) -> Any:
        kwargs = {
            "model": self.model,
            "messages": messages
        }
        if tools:
            kwargs["tools"] = tools
            
        response = await self.client.chat.completions.create(**kwargs)
        return response.choices[0].message
