from __future__ import annotations

from dataclasses import dataclass

from src.meridian.application.pipeline.reliability_policy import CoverageThresholds, ReliabilityPolicy


@dataclass(frozen=True)
class CoverageVerdict:
    domain: str
    action: str
    reason: str
    accepted_count: int
    distinct_sources: int
    average_relevance: float
    source_distribution: dict[str, int]
    query_family_distribution: dict[str, int]
    required_documents: int
    required_sources: int
    required_average_relevance: float

    def failure_message(self) -> str:
        return (
            "Insufficient relevant evidence: "
            f"{self.reason} for domain '{self.domain}' "
            f"(accepted={self.accepted_count}/{self.required_documents}, "
            f"sources={self.distinct_sources}/{self.required_sources}, "
            f"average_relevance={self.average_relevance:.2f}/{self.required_average_relevance:.2f}, "
            f"source_distribution={self.source_distribution})"
        )


class InsufficientRelevantEvidenceError(RuntimeError):
    def __init__(self, verdict: CoverageVerdict):
        self.verdict = verdict
        super().__init__(verdict.failure_message())


class CoverageGate:
    def __init__(self, policy: ReliabilityPolicy):
        self.policy = policy

    def evaluate(
        self,
        domain: str,
        accepted_count: int,
        distinct_sources: int,
        average_relevance: float,
        source_distribution: dict[str, int] | None = None,
        query_family_distribution: dict[str, int] | None = None,
    ) -> CoverageVerdict:
        thresholds = self.policy.coverage_for(domain)
        normalized_source_distribution = dict(source_distribution or {})
        normalized_query_family_distribution = dict(query_family_distribution or {})
        reason = self._reason(
            thresholds,
            accepted_count,
            distinct_sources,
            average_relevance,
            normalized_source_distribution,
            normalized_query_family_distribution,
        )
        action = "synthesize" if reason == "sufficient_coverage" else "retry"
        return CoverageVerdict(
            domain=domain,
            action=action,
            reason=reason,
            accepted_count=accepted_count,
            distinct_sources=distinct_sources,
            average_relevance=average_relevance,
            source_distribution=normalized_source_distribution,
            query_family_distribution=normalized_query_family_distribution,
            required_documents=thresholds.min_documents,
            required_sources=thresholds.min_sources,
            required_average_relevance=thresholds.min_average_relevance,
        )

    def _reason(
        self,
        thresholds: CoverageThresholds,
        accepted_count: int,
        distinct_sources: int,
        average_relevance: float,
        source_distribution: dict[str, int],
        query_family_distribution: dict[str, int],
    ) -> str:
        if accepted_count < thresholds.min_documents:
            return "insufficient_documents"
        if distinct_sources < thresholds.min_sources:
            return "insufficient_sources"
        if self._is_source_skewed(accepted_count, source_distribution):
            return "insufficient_source_balance"
        if any(count > 2 for count in query_family_distribution.values()):
            return "insufficient_query_family_diversity"
        if average_relevance < thresholds.min_average_relevance:
            return "insufficient_relevance"
        return "sufficient_coverage"

    def _is_source_skewed(self, accepted_count: int, source_distribution: dict[str, int]) -> bool:
        if accepted_count <= 0 or len(source_distribution) <= 1:
            return False
        max_share = max(source_distribution.values(), default=0) / accepted_count
        return max_share > 0.6
