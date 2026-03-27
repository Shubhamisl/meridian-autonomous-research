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


class PipelinePayload(BaseModel):
    current_phase: str | None = None
    phases: list[str] = Field(default_factory=list)


class ExplainabilityPayload(BaseModel):
    active_sources: list[str] = Field(default_factory=list)
    query_refinements: list[QueryRefinement] = Field(default_factory=list)


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
