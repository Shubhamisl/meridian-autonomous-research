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

    def _normalize_label(self, raw_label: str) -> str:
        label = raw_label.strip().lower()
        if ":" in label:
            prefix, suffix = label.split(":", 1)
            if prefix.strip() in {"label", "domain", "category", "classification"}:
                label = suffix.strip()

        label = label.strip("\"'`.,:;!?")
        label = "_".join(label.replace("-", " ").split())

        aliases = {
            "computer science": "computer_science",
            "computer_science": "computer_science",
            "biomedical": "biomedical",
            "economics": "economics",
            "legal": "legal",
            "general": "general",
        }
        return aliases.get(label, label)

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
        label = self._normalize_label(getattr(response, "content", "") or "")
        if label in self.ALLOWED_LABELS:
            return label
        return "general"
