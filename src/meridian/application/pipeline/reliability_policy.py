from dataclasses import dataclass


@dataclass(frozen=True)
class RelevanceThresholds:
    auto_reject_below: float = 0.45
    borderline_below: float = 0.70
    final_accept_below: float = 0.60
    llm_budget: int = 5


@dataclass(frozen=True)
class CoverageThresholds:
    min_documents: int
    min_sources: int
    min_average_relevance: float


class ReliabilityPolicy:
    def __init__(self) -> None:
        self.relevance = RelevanceThresholds()
        self._coverage = {
            "biomedical": CoverageThresholds(min_documents=3, min_sources=2, min_average_relevance=0.70),
            "computer_science": CoverageThresholds(min_documents=3, min_sources=2, min_average_relevance=0.68),
            "economics": CoverageThresholds(min_documents=3, min_sources=2, min_average_relevance=0.68),
            "legal": CoverageThresholds(min_documents=3, min_sources=2, min_average_relevance=0.70),
            "general": CoverageThresholds(min_documents=2, min_sources=1, min_average_relevance=0.65),
        }

    def coverage_for(self, domain: str) -> CoverageThresholds:
        domain_key = domain.lower() if isinstance(domain, str) else "general"
        return self._coverage.get(domain_key, self._coverage["general"])
