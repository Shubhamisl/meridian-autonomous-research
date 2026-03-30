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


@dataclass(frozen=True)
class EvidenceSelectionResult:
    accepted: list[EvidenceDecision]
    rejected: list[EvidenceDecision]


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

        for group in self._deduplicate(candidates):
            representative = group[0]
            assessment = await self.relevance_scorer.score(query, representative)
            decision = self._decision_from_assessment(representative, assessment)

            if decision.reason == "accepted":
                accepted.append(decision)
            else:
                rejected.append(decision)

            for duplicate in group[1:]:
                rejected.append(
                    EvidenceDecision(
                        document=duplicate,
                        reason="duplicate",
                        relevance_score=assessment.score,
                    )
                )

        return EvidenceSelectionResult(accepted=accepted, rejected=rejected)

    def _decision_from_assessment(self, document: Document, assessment: RelevanceAssessment) -> EvidenceDecision:
        relevance = self.policy.relevance

        if assessment.score < relevance.auto_reject_below:
            return EvidenceDecision(document=document, reason="low_relevance", relevance_score=assessment.score)

        if assessment.score >= relevance.borderline_below:
            return EvidenceDecision(document=document, reason="accepted", relevance_score=assessment.score)

        if assessment.llm_success and assessment.score >= relevance.final_accept_below:
            return EvidenceDecision(document=document, reason="accepted", relevance_score=assessment.score)

        if assessment.llm_attempted:
            return EvidenceDecision(document=document, reason="borderline_fallback", relevance_score=assessment.score)

        return EvidenceDecision(document=document, reason="borderline_rejected", relevance_score=assessment.score)

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
