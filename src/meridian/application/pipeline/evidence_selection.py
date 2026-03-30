from __future__ import annotations

from dataclasses import dataclass

from src.meridian.application.pipeline.relevance_scorer import RelevanceAssessment, RelevanceScorer
from src.meridian.application.pipeline.reliability_policy import ReliabilityPolicy
from src.meridian.domain.entities import Document


@dataclass(frozen=True)
class EvidenceDecision:
    document: Document
    reason: str
    relevance_score: float
    scorer_reason: str
    scorer_detail: str | None = None
    adjudication_detail: str | None = None
    source_query: str | None = None
    llm_attempted: bool = False
    llm_success: bool = False


@dataclass(frozen=True)
class EvidenceSelectionResult:
    query: str
    domain: str
    source_queries: dict[str, str]
    accepted: list[EvidenceDecision]
    rejected: list[EvidenceDecision]
    llm_budget_limit: int
    llm_budget_used: int
    llm_budget_remaining: int


class EvidenceSelectionService:
    def __init__(
        self,
        policy: ReliabilityPolicy,
        relevance_scorer: RelevanceScorer | None = None,
    ) -> None:
        self.policy = policy
        self.relevance_scorer = relevance_scorer or RelevanceScorer(policy=policy)

    async def select(
        self,
        query: str,
        domain: str,
        candidates: list[Document],
        source_queries: dict[str, str],
    ) -> EvidenceSelectionResult:
        accepted: list[EvidenceDecision] = []
        rejected: list[EvidenceDecision] = []
        remaining_budget = self.policy.relevance.llm_budget
        used_budget = 0

        for group in self._deduplicate(candidates):
            representative = group[0]
            assessment = await self.relevance_scorer.score(
                query,
                representative,
                llm_budget_remaining=remaining_budget,
            )
            decision = self._decision_from_assessment(
                representative,
                assessment,
                source_query=self._source_query_for(representative, source_queries),
            )

            if decision.reason == "accepted":
                accepted.append(decision)
            else:
                rejected.append(decision)

            if assessment.llm_attempted:
                used_budget += 1
                remaining_budget = max(0, remaining_budget - 1)

            for duplicate in group[1:]:
                rejected.append(
                    EvidenceDecision(
                        document=duplicate,
                        reason="duplicate",
                        relevance_score=assessment.score,
                        scorer_reason=assessment.reason,
                        scorer_detail=assessment.detail,
                        adjudication_detail=assessment.detail,
                        source_query=self._source_query_for(duplicate, source_queries),
                        llm_attempted=assessment.llm_attempted,
                        llm_success=assessment.llm_success,
                    )
                )

        return EvidenceSelectionResult(
            query=query,
            domain=domain,
            source_queries=dict(source_queries),
            accepted=accepted,
            rejected=rejected,
            llm_budget_limit=self.policy.relevance.llm_budget,
            llm_budget_used=used_budget,
            llm_budget_remaining=remaining_budget,
        )

    def _decision_from_assessment(
        self,
        document: Document,
        assessment: RelevanceAssessment,
        source_query: str | None,
    ) -> EvidenceDecision:
        relevance = self.policy.relevance

        if assessment.score < relevance.auto_reject_below:
            return EvidenceDecision(
                document=document,
                reason="low_relevance",
                relevance_score=assessment.score,
                scorer_reason=assessment.reason,
                scorer_detail=assessment.detail,
                adjudication_detail=assessment.detail,
                source_query=source_query,
                llm_attempted=assessment.llm_attempted,
                llm_success=assessment.llm_success,
            )

        if assessment.score >= relevance.borderline_below:
            return EvidenceDecision(
                document=document,
                reason="accepted",
                relevance_score=assessment.score,
                scorer_reason=assessment.reason,
                scorer_detail=assessment.detail,
                adjudication_detail=assessment.detail,
                source_query=source_query,
                llm_attempted=assessment.llm_attempted,
                llm_success=assessment.llm_success,
            )

        if assessment.llm_success and assessment.score >= relevance.final_accept_below:
            return EvidenceDecision(
                document=document,
                reason="accepted",
                relevance_score=assessment.score,
                scorer_reason=assessment.reason,
                scorer_detail=assessment.detail,
                adjudication_detail=assessment.detail,
                source_query=source_query,
                llm_attempted=assessment.llm_attempted,
                llm_success=assessment.llm_success,
            )

        if assessment.llm_attempted:
            return EvidenceDecision(
                document=document,
                reason="borderline_fallback",
                relevance_score=assessment.score,
                scorer_reason=assessment.reason,
                scorer_detail=assessment.detail,
                adjudication_detail=assessment.detail,
                source_query=source_query,
                llm_attempted=assessment.llm_attempted,
                llm_success=assessment.llm_success,
            )

        return EvidenceDecision(
            document=document,
            reason="borderline_rejected",
            relevance_score=assessment.score,
            scorer_reason=assessment.reason,
            scorer_detail=assessment.detail,
            adjudication_detail=assessment.detail,
            source_query=source_query,
            llm_attempted=assessment.llm_attempted,
            llm_success=assessment.llm_success,
        )

    def _deduplicate(self, candidates: list[Document]) -> list[list[Document]]:
        grouped: dict[tuple[str, str, str, str], list[Document]] = {}
        order: list[tuple[str, str, str, str]] = []

        for document in candidates:
            key = (
                self._normalize(document.source),
                self._normalize(document.title),
                self._normalize(document.url),
                self._normalize(document.content),
            )
            if key not in grouped:
                grouped[key] = []
                order.append(key)
            grouped[key].append(document)

        return [grouped[key] for key in order]

    def _normalize(self, value: str) -> str:
        return " ".join(value.lower().split()) if isinstance(value, str) else ""

    def _source_query_for(self, document: Document, source_queries: dict[str, str]) -> str | None:
        source = self._normalize(document.source)
        return source_queries.get(source) or source_queries.get(document.source) or source_queries.get(document.source.lower())
