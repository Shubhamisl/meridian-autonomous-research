from src.meridian.infrastructure.llm.openrouter_client import OpenRouterClient


class DomainClassifier:
    ALLOWED_LABELS = {
        "biomedical",
        "computer_science",
        "economics",
        "legal",
        "general",
    }

    def __init__(self, openrouter_client: OpenRouterClient):
        self.llm = openrouter_client

    async def classify(self, query: str) -> str:
        messages = [
            {
                "role": "system",
                "content": (
                    "Classify the user's query into exactly one label from "
                    "biomedical, computer_science, economics, legal, general. "
                    "Return only the label text and nothing else."
                ),
            },
            {"role": "user", "content": query},
        ]

        response = await self.llm.generate_response(messages=messages)
        label = (getattr(response, "content", "") or "").strip().lower()
        if label in self.ALLOWED_LABELS:
            return label
        return "general"
