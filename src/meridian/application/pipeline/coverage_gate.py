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
    required_documents: int
    required_sources: int
    required_average_relevance: float

    def failure_message(self) -> str:
        return (
            "Insufficient relevant evidence: "
            f"{self.reason} for domain '{self.domain}' "
            f"(accepted={self.accepted_count}/{self.required_documents}, "
            f"sources={self.distinct_sources}/{self.required_sources}, "
            f"average_relevance={self.average_relevance:.2f}/{self.required_average_relevance:.2f})"
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
    ) -> CoverageVerdict:
        thresholds = self.policy.coverage_for(domain)
        reason = self._reason(thresholds, accepted_count, distinct_sources, average_relevance)
        action = "synthesize" if reason == "sufficient_coverage" else "retry"
        return CoverageVerdict(
            domain=domain,
            action=action,
            reason=reason,
            accepted_count=accepted_count,
            distinct_sources=distinct_sources,
            average_relevance=average_relevance,
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
    ) -> str:
        if accepted_count < thresholds.min_documents:
            return "insufficient_documents"
        if distinct_sources < thresholds.min_sources:
            return "insufficient_sources"
        if average_relevance < thresholds.min_average_relevance:
            return "insufficient_relevance"
        return "sufficient_coverage"
