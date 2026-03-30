from pydantic import BaseModel, Field


class EvidenceItem(BaseModel):
    source: str
    title: str
    url: str | None = None
    credibility_score: float = 0.5
    snippet: str | None = None


class QueryRefinement(BaseModel):
    source: str
    raw_query: str
    enriched_query: str


class SelectionDecisionPayload(BaseModel):
    document_id: str | None = None
    source: str | None = None
    title: str | None = None
    url: str | None = None
    reason: str
    relevance_score: float
    scorer_reason: str | None = None
    scorer_detail: str | None = None
    adjudication_detail: str | None = None
    source_query: str | None = None
    credibility_score: float | None = None
    llm_attempted: bool = False
    llm_success: bool = False


class SelectionPayload(BaseModel):
    accepted_count: int = 0
    rejected_count: int = 0
    source_queries: dict[str, list[str]] = Field(default_factory=dict)
    llm_budget_limit: int | None = None
    llm_budget_used: int | None = None
    llm_budget_remaining: int | None = None
    accepted: list[SelectionDecisionPayload] = Field(default_factory=list)
    rejected: list[SelectionDecisionPayload] = Field(default_factory=list)


class CoveragePayload(BaseModel):
    action: str | None = None
    reason: str | None = None
    accepted_count: int | None = None
    distinct_sources: int | None = None
    average_relevance: float | None = None
    source_distribution: dict[str, int] = Field(default_factory=dict)
    query_family_distribution: dict[str, int] = Field(default_factory=dict)
    required_documents: int | None = None
    required_sources: int | None = None
    required_average_relevance: float | None = None
    message: str | None = None


class PipelinePayload(BaseModel):
    current_phase: str | None = None
    phases: list[str] = Field(default_factory=list)


class ExplainabilityPayload(BaseModel):
    active_sources: list[str] = Field(default_factory=list)
    query_refinements: list[QueryRefinement] = Field(default_factory=list)
    selection: SelectionPayload | None = None
    coverage: CoveragePayload | None = None


class ResearchWorkspaceResponse(BaseModel):
    id: str
    job_id: str
    query: str
    markdown_content: str
    domain: str | None = None
    format_label: str | None = None
    pipeline: PipelinePayload
    evidence: list[EvidenceItem] = Field(default_factory=list)
    explainability: ExplainabilityPayload
