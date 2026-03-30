from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from src.meridian.application.pipeline.reliability_policy import ReliabilityPolicy
from src.meridian.domain.entities import Document
from src.meridian.infrastructure.llm.openrouter_client import OpenRouterClient


@dataclass(frozen=True)
class RelevanceAssessment:
    score: float
    reason: str
    llm_attempted: bool = False
    llm_success: bool = False


class RelevanceScorer:
    def __init__(
        self,
        openrouter_client: OpenRouterClient | None = None,
        policy: ReliabilityPolicy | None = None,
    ) -> None:
        self.client = openrouter_client
        self.policy = policy or ReliabilityPolicy()
        self._llm_calls_used = 0

    async def score(self, query: str, document: Document) -> RelevanceAssessment:
        lexical_score = self._lexical_score(query, document)
        relevance = self.policy.relevance

        if lexical_score < relevance.auto_reject_below:
            return RelevanceAssessment(score=lexical_score, reason="lexical_mismatch")

        if lexical_score >= relevance.borderline_below:
            return RelevanceAssessment(score=lexical_score, reason="lexically_relevant")

        if self.client is None or self._llm_calls_used >= relevance.llm_budget:
            return RelevanceAssessment(score=lexical_score, reason="borderline_fallback")

        self._llm_calls_used += 1
        try:
            response = await self.client.generate_response(messages=self._build_messages(query, document))
            parsed = self._parse_llm_score(getattr(response, "content", ""))
            if parsed is None:
                return RelevanceAssessment(
                    score=lexical_score,
                    reason="borderline_fallback",
                    llm_attempted=True,
                    llm_success=False,
                )
            return RelevanceAssessment(
                score=parsed,
                reason="llm_adjudicated",
                llm_attempted=True,
                llm_success=True,
            )
        except Exception:
            return RelevanceAssessment(
                score=lexical_score,
                reason="borderline_fallback",
                llm_attempted=True,
                llm_success=False,
            )

    def _lexical_score(self, query: str, document: Document) -> float:
        query_terms = self._terms(query)
        if not query_terms:
            return 0.0

        document_terms = self._terms(f"{document.title} {document.content}")
        if not document_terms:
            return 0.0

        overlap = len(query_terms & document_terms)
        return max(0.0, min(1.0, overlap / len(query_terms)))

    def _terms(self, text: str) -> set[str]:
        return {token for token in re.findall(r"[A-Za-z0-9]+", text.lower()) if len(token) > 2}

    def _build_messages(self, query: str, document: Document) -> list[dict[str, str]]:
        return [
            {
                "role": "system",
                "content": (
                    "You score topical relevance. Return strict JSON only with "
                    '{"score": 0.0-1.0, "reason": "brief explanation"}. No markdown, no extra text.'
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Query: {query}\n"
                    f"Source: {document.source}\n"
                    f"Title: {document.title}\n"
                    f"Content: {document.content}"
                ),
            },
        ]

    def _parse_llm_score(self, payload: str) -> float | None:
        try:
            data: Any = json.loads(payload)
        except (TypeError, json.JSONDecodeError):
            return None

        score = data.get("score")
        if isinstance(score, bool) or not isinstance(score, (int, float)):
            return None

        score = float(score)
        if 0.0 <= score <= 1.0:
            return score
        return None
