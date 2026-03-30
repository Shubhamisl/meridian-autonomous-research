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
    detail: str | None = None
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

    async def score(
        self,
        query: str,
        document: Document,
        llm_budget_remaining: int | None = None,
    ) -> RelevanceAssessment:
        return await self._score(query, document, llm_budget_remaining=llm_budget_remaining)

    async def _score(
        self,
        query: str,
        document: Document,
        llm_budget_remaining: int | None,
    ) -> RelevanceAssessment:
        lexical_score = self._lexical_score(query, document)
        relevance = self.policy.relevance

        if lexical_score < relevance.auto_reject_below:
            return RelevanceAssessment(score=lexical_score, reason="lexical_mismatch")

        if lexical_score >= relevance.borderline_below:
            return RelevanceAssessment(score=lexical_score, reason="lexically_relevant")

        budget = relevance.llm_budget if llm_budget_remaining is None else llm_budget_remaining
        if self.client is None or budget <= 0:
            return RelevanceAssessment(score=lexical_score, reason="borderline_fallback")

        try:
            response = await self.client.generate_response(messages=self._build_messages(query, document))
            parsed = self._parse_llm_payload(getattr(response, "content", ""))
            if parsed is None:
                return RelevanceAssessment(
                    score=lexical_score,
                    reason="borderline_fallback",
                    detail="invalid_llm_response",
                    llm_attempted=True,
                    llm_success=False,
                )
            return RelevanceAssessment(
                score=parsed["score"],
                reason="llm_adjudicated",
                detail=parsed.get("reason"),
                llm_attempted=True,
                llm_success=True,
            )
        except Exception:
            return RelevanceAssessment(
                score=lexical_score,
                reason="borderline_fallback",
                detail="llm_error",
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
        terms: set[str] = set()
        for token in re.findall(r"[A-Za-z0-9]+", text):
            normalized = self._normalize_token(token)
            if normalized is not None:
                terms.add(normalized)
        return terms

    def _normalize_token(self, token: str) -> str | None:
        if len(token) > 2:
            return token.lower()

        if token.isalpha() and len(token) == 2:
            normalized = token.upper()
            if normalized in {"AI", "ML", "EU", "US", "UK"}:
                return normalized

        return None

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

    def _parse_llm_payload(self, payload: str) -> dict[str, Any] | None:
        try:
            data: Any = json.loads(payload)
        except (TypeError, json.JSONDecodeError):
            return None

        score = data.get("score")
        if isinstance(score, bool) or not isinstance(score, (int, float)):
            return None

        score = float(score)
        if 0.0 <= score <= 1.0:
            reason = data.get("reason")
            return {"score": score, "reason": reason if isinstance(reason, str) else None}
        return None
