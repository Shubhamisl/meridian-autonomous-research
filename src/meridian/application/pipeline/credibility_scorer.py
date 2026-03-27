import json
import os

from src.meridian.domain.entities import Document
from src.meridian.infrastructure.llm.openrouter_client import OpenRouterClient


class CredibilityScorer:
    HEURISTIC_SCORES = {
        "pubmed": 0.92,
        "ieee": 0.90,
        "arxiv": 0.82,
        "semantic_scholar": 0.78,
        "wikipedia": 0.65,
        "web": 0.40,
    }

    def __init__(self, openrouter_client: OpenRouterClient, web_audit_limit: int | None = None):
        self.llm = openrouter_client
        self.web_audit_limit = (
            web_audit_limit if web_audit_limit is not None else int(os.getenv("WEB_CREDIBILITY_AUDIT_LIMIT", "5"))
        )
        self.web_audits_used = 0

    def _heuristic_score(self, document: Document) -> float:
        return self.HEURISTIC_SCORES.get(document.source.lower(), self.HEURISTIC_SCORES["web"])

    def _build_messages(self, document: Document) -> list[dict[str, str]]:
        return [
            {
                "role": "system",
                "content": (
                    "You are auditing web-source credibility. Return strict JSON only with "
                    '{"score": 0.0-1.0, "reason": "brief explanation"}. No markdown, no extra text.'
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Source: {document.source}\n"
                    f"Title: {document.title}\n"
                    f"URL: {document.url}\n"
                    f"Content: {document.content}"
                ),
            },
        ]

    def _parse_llm_score(self, payload: str) -> float | None:
        try:
            data = json.loads(payload)
        except (TypeError, json.JSONDecodeError):
            return None

        score = data.get("score")
        if isinstance(score, bool) or not isinstance(score, (int, float)):
            return None

        score = float(score)
        if 0.0 <= score <= 1.0:
            return score
        return None

    async def score(self, document: Document) -> float:
        heuristic = self._heuristic_score(document)
        if document.source.lower() != "web":
            return heuristic

        if self.web_audits_used >= self.web_audit_limit:
            return heuristic

        self.web_audits_used += 1
        try:
            response = await self.llm.generate_response(messages=self._build_messages(document))
            parsed_score = self._parse_llm_score(getattr(response, "content", ""))
            return parsed_score if parsed_score is not None else heuristic
        except Exception:
            return heuristic
