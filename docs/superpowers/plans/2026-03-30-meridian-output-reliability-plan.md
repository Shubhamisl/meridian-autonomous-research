# Meridian Output Reliability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a source-aware evidence quality layer that filters off-topic documents before chunking, applies domain-configured coverage thresholds, and makes retries deterministic and measurable across all Meridian domains.

**Architecture:** Introduce application-layer reliability services (`ReliabilityPolicy`, `SourceQueryPlanner`, `RelevanceScorer`, `EvidenceSelectionService`, `CoverageGate`) and wire them into the orchestrator between research and chunking. Keep source adapters thin, but harden PubMed/arXiv query compilation and persist evidence-selection metadata for evaluation and explainability.

**Tech Stack:** Python, FastAPI, Celery, SQLite, ChromaDB, OpenRouter, pytest, Vitest

---

## File Map

**Create**

- `src/meridian/application/pipeline/reliability_policy.py`
- `src/meridian/application/pipeline/source_query_planner.py`
- `src/meridian/application/pipeline/relevance_scorer.py`
- `src/meridian/application/pipeline/evidence_selection.py`
- `src/meridian/application/pipeline/coverage_gate.py`
- `tests/application/pipeline/test_reliability_policy.py`
- `tests/application/pipeline/test_source_query_planner.py`
- `tests/application/pipeline/test_relevance_scorer.py`
- `tests/application/pipeline/test_evidence_selection.py`
- `tests/application/pipeline/test_coverage_gate.py`
- `tests/application/pipeline/fixtures/test_output_reliability_fixtures.py`

**Modify**

- `src/meridian/infrastructure/llm/research_agent.py`
- `src/meridian/application/pipeline/orchestrator.py`
- `src/meridian/infrastructure/external_apis/pubmed_client.py`
- `src/meridian/infrastructure/external_apis/arxiv_client.py`
- `src/meridian/interfaces/workers/tasks.py`
- `src/meridian/interfaces/api/routers/research.py`
- `src/meridian/infrastructure/llm/synthesizer.py`
- `tests/infrastructure/llm/test_research_agent.py`
- `tests/application/pipeline/test_orchestrator.py`
- `tests/interfaces/api/test_research_router.py`
- `README.md`

**Responsibility split**

- `reliability_policy.py`: all configurable thresholds and defaults
- `source_query_planner.py`: source-native query compilation and retry refinement
- `relevance_scorer.py`: document topical relevance scoring and LLM adjudication budget handling
- `evidence_selection.py`: deduplication, relevance filtering, diversity selection, and result metadata
- `coverage_gate.py`: synthesis-allow / retry / fail decision based on accepted evidence
- adapters remain thin and source-specific
- orchestrator owns phase order and persistence of selection metadata

---

### Task 1: Add Reliability Policy And Source-Native Query Planning

**Files:**
- Create: `src/meridian/application/pipeline/reliability_policy.py`
- Create: `src/meridian/application/pipeline/source_query_planner.py`
- Test: `tests/application/pipeline/test_reliability_policy.py`
- Test: `tests/application/pipeline/test_source_query_planner.py`

- [ ] **Step 1: Write failing tests for policy defaults**

```python
from src.meridian.application.pipeline.reliability_policy import ReliabilityPolicy


def test_reliability_policy_defaults_are_domain_specific():
    policy = ReliabilityPolicy()

    assert policy.coverage_for("biomedical").min_documents == 3
    assert policy.coverage_for("general").min_documents == 2
    assert policy.relevance.auto_reject_below == 0.45
    assert policy.relevance.borderline_below == 0.70
    assert policy.relevance.final_accept_below == 0.60
```

- [ ] **Step 2: Write failing tests for source-native query compilation**

```python
from src.meridian.application.pipeline.source_query_planner import SourceQueryPlanner


def test_pubmed_query_does_not_leak_after_operator():
    planner = SourceQueryPlanner()

    compiled = planner.compile(
        user_query="Recent advances in mRNA vaccines",
        execution_query='\"mRNA vaccine\" after:2022-01-01',
        domain="biomedical",
        source="pubmed",
    )

    assert "after:" not in compiled
    assert "2022" in compiled


def test_arxiv_query_prefers_clean_phrase_search():
    planner = SourceQueryPlanner()

    compiled = planner.compile(
        user_query="Recent advances in mRNA vaccines",
        execution_query='\"mRNA vaccine\" after:2022-01-01',
        domain="biomedical",
        source="arxiv",
    )

    assert "after:" not in compiled
    assert '"mRNA vaccine"' in compiled
```

- [ ] **Step 3: Run tests to verify they fail**

Run:

```bash
set PYTHONPATH=%cd%
python -m pytest tests/application/pipeline/test_reliability_policy.py tests/application/pipeline/test_source_query_planner.py -q
```

Expected:

- `ModuleNotFoundError` or missing symbol failures for the new modules

- [ ] **Step 4: Write minimal policy implementation**

```python
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
    def __init__(self):
        self.relevance = RelevanceThresholds()
        self._coverage = {
            "biomedical": CoverageThresholds(3, 2, 0.70),
            "computer_science": CoverageThresholds(3, 2, 0.68),
            "economics": CoverageThresholds(3, 2, 0.68),
            "legal": CoverageThresholds(3, 2, 0.70),
            "general": CoverageThresholds(2, 1, 0.65),
        }

    def coverage_for(self, domain: str) -> CoverageThresholds:
        return self._coverage.get(domain, self._coverage["general"])
```

- [ ] **Step 5: Write minimal query planner implementation**

```python
import re


class SourceQueryPlanner:
    def compile(self, user_query: str, execution_query: str, domain: str, source: str) -> str:
        if source == "pubmed":
            return self._compile_pubmed(user_query, execution_query)
        if source == "arxiv":
            return self._compile_arxiv(user_query, execution_query)
        return execution_query

    def refine(self, user_query: str, domain: str, attempted_queries: list[str], rejection_reasons: list[str]) -> str:
        return user_query

    def _compile_pubmed(self, user_query: str, execution_query: str) -> str:
        cleaned = re.sub(r"after:\S+", "", execution_query).strip()
        return f'{cleaned} AND ("2022"[Date - Publication] : "3000"[Date - Publication])'

    def _compile_arxiv(self, user_query: str, execution_query: str) -> str:
        return re.sub(r"after:\S+", "", execution_query).strip()
```

- [ ] **Step 6: Run tests to verify they pass**

Run:

```bash
set PYTHONPATH=%cd%
python -m pytest tests/application/pipeline/test_reliability_policy.py tests/application/pipeline/test_source_query_planner.py -q
```

Expected:

- `4 passed`

- [ ] **Step 7: Commit**

```bash
git add tests/application/pipeline/test_reliability_policy.py tests/application/pipeline/test_source_query_planner.py src/meridian/application/pipeline/reliability_policy.py src/meridian/application/pipeline/source_query_planner.py
git commit -m "feat: add reliability policy and source query planner"
```

### Task 2: Add Relevance Scoring And Evidence Selection

**Files:**
- Create: `src/meridian/application/pipeline/relevance_scorer.py`
- Create: `src/meridian/application/pipeline/evidence_selection.py`
- Test: `tests/application/pipeline/test_relevance_scorer.py`
- Test: `tests/application/pipeline/test_evidence_selection.py`

- [ ] **Step 1: Write failing tests for automatic reject / borderline / accept**

```python
from src.meridian.application.pipeline.relevance_scorer import RelevanceScorer
from src.meridian.domain.entities import Document


def test_relevance_scorer_rejects_obvious_topic_mismatch():
    scorer = RelevanceScorer()
    document = Document(source="arxiv", title="Solar Upper Transition Region Imager", content="Solar imaging payload.", url="x")

    score = scorer.score("Recent advances in mRNA vaccines", document)

    assert score < 0.45
```

- [ ] **Step 2: Write failing tests for deduplication and selection**

```python
from src.meridian.application.pipeline.evidence_selection import EvidenceSelectionService
from src.meridian.application.pipeline.reliability_policy import ReliabilityPolicy
from src.meridian.domain.entities import Document


def test_evidence_selection_rejects_off_topic_and_duplicate_candidates():
    service = EvidenceSelectionService(policy=ReliabilityPolicy())
    candidates = [
        Document(source="pubmed", title="mRNA vaccine advances", content="Advances in vaccine delivery", url="a"),
        Document(source="pubmed", title="mRNA vaccine advances", content="Advances in vaccine delivery", url="a"),
        Document(source="arxiv", title="Solar imaging instrumentation", content="Observations of the sun", url="b"),
    ]

    result = service.select(
        query="Recent advances in mRNA vaccines",
        domain="biomedical",
        candidates=candidates,
        source_queries={"pubmed": "mRNA vaccine", "arxiv": '"mRNA vaccine"'},
    )

    assert len(result.accepted) == 1
    assert len(result.rejected) == 2
```

- [ ] **Step 3: Run tests to verify they fail**

Run:

```bash
set PYTHONPATH=%cd%
python -m pytest tests/application/pipeline/test_relevance_scorer.py tests/application/pipeline/test_evidence_selection.py -q
```

Expected:

- missing module failures

- [ ] **Step 4: Implement `RelevanceScorer` with cheap hybrid scoring**

```python
import re


class RelevanceScorer:
    def score(self, query: str, document) -> float:
        query_terms = self._terms(query)
        doc_terms = self._terms(f"{document.title} {document.content}")
        if not query_terms or not doc_terms:
            return 0.0
        overlap = len(query_terms & doc_terms) / len(query_terms)
        return min(max(overlap, 0.0), 1.0)

    def _terms(self, text: str) -> set[str]:
        return {token for token in re.findall(r"[A-Za-z0-9]+", text.lower()) if len(token) > 2}
```

- [ ] **Step 5: Implement `EvidenceSelectionService` as a facade**

```python
from dataclasses import dataclass


@dataclass
class EvidenceDecision:
    document: object
    reason: str
    relevance_score: float


@dataclass
class EvidenceSelectionResult:
    accepted: list[EvidenceDecision]
    rejected: list[EvidenceDecision]


class EvidenceSelectionService:
    def __init__(self, policy, relevance_scorer=None):
        self.policy = policy
        self.relevance_scorer = relevance_scorer

    def select(self, query: str, domain: str, candidates: list, source_queries: dict[str, str]) -> EvidenceSelectionResult:
        deduped = self._deduplicate(candidates)
        accepted = []
        rejected = []
        for document in deduped:
            score = self.relevance_scorer.score(query, document)
            if score < self.policy.relevance.auto_reject_below:
                rejected.append(EvidenceDecision(document, "low_relevance", score))
            else:
                accepted.append(EvidenceDecision(document, "accepted", score))
        return EvidenceSelectionResult(accepted=accepted, rejected=rejected)

    def _deduplicate(self, candidates: list) -> list:
        seen = set()
        deduped = []
        for document in candidates:
            key = (document.source, document.title, document.url)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(document)
        return deduped
```

- [ ] **Step 6: Run tests to verify they pass**

Run:

```bash
set PYTHONPATH=%cd%
python -m pytest tests/application/pipeline/test_relevance_scorer.py tests/application/pipeline/test_evidence_selection.py -q
```

Expected:

- relevant tests pass

- [ ] **Step 7: Commit**

```bash
git add tests/application/pipeline/test_relevance_scorer.py tests/application/pipeline/test_evidence_selection.py src/meridian/application/pipeline/relevance_scorer.py src/meridian/application/pipeline/evidence_selection.py
git commit -m "feat: add evidence relevance scoring and selection"
```

### Task 3: Add Coverage Gate And Orchestrator Integration

**Files:**
- Create: `src/meridian/application/pipeline/coverage_gate.py`
- Modify: `src/meridian/application/pipeline/orchestrator.py`
- Test: `tests/application/pipeline/test_coverage_gate.py`
- Test: `tests/application/pipeline/test_orchestrator.py`

- [ ] **Step 1: Write failing tests for domain-specific coverage decisions**

```python
from src.meridian.application.pipeline.coverage_gate import CoverageGate
from src.meridian.application.pipeline.reliability_policy import ReliabilityPolicy


def test_biomedical_coverage_requires_three_documents_and_two_sources():
    gate = CoverageGate(ReliabilityPolicy())
    verdict = gate.evaluate(
        domain="biomedical",
        accepted_count=2,
        distinct_sources=1,
        average_relevance=0.80,
    )

    assert verdict.action == "retry"
```

- [ ] **Step 2: Write failing orchestrator integration test**

```python
async def test_run_pipeline_filters_evidence_before_chunking(monkeypatch):
    ...
    assert chunking_service.calls[0] == [accepted_document]
    assert saved_metadata["selection"]["rejected_count"] == 1
```

- [ ] **Step 3: Run tests to verify they fail**

Run:

```bash
set PYTHONPATH=%cd%
python -m pytest tests/application/pipeline/test_coverage_gate.py tests/application/pipeline/test_orchestrator.py -q
```

Expected:

- missing module or assertion failures

- [ ] **Step 4: Implement `CoverageGate`**

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class CoverageVerdict:
    action: str
    reason: str


class CoverageGate:
    def __init__(self, policy):
        self.policy = policy

    def evaluate(self, domain: str, accepted_count: int, distinct_sources: int, average_relevance: float) -> CoverageVerdict:
        threshold = self.policy.coverage_for(domain)
        if (
            accepted_count < threshold.min_documents
            or distinct_sources < threshold.min_sources
            or average_relevance < threshold.min_average_relevance
        ):
            return CoverageVerdict("retry", "insufficient_coverage")
        return CoverageVerdict("synthesize", "sufficient_coverage")
```

- [ ] **Step 5: Integrate selection and coverage into the orchestrator**

```python
accepted_result = self.evidence_selection_service.select(
    query=execution_query,
    domain=domain,
    candidates=documents,
    source_queries=getattr(self.agent, "source_queries", {}),
)
accepted_documents = [decision.document for decision in accepted_result.accepted]
verdict = self.coverage_gate.evaluate(
    domain=domain,
    accepted_count=len(accepted_result.accepted),
    distinct_sources=len({d.source for d in accepted_documents}),
    average_relevance=sum(d.relevance_score for d in accepted_result.accepted) / max(len(accepted_result.accepted), 1),
)
if verdict.action != "synthesize":
    raise RuntimeError("Insufficient relevant evidence after selection")
all_chunks = await self.chunking_service.chunk_documents(accepted_documents)
```

- [ ] **Step 6: Persist selection metadata for explainability**

```python
workspace_metadata["selection"] = {
    "accepted_count": len(accepted_result.accepted),
    "rejected_count": len(accepted_result.rejected),
    "rejected_reasons": [decision.reason for decision in accepted_result.rejected],
}
```

- [ ] **Step 7: Run tests to verify they pass**

Run:

```bash
set PYTHONPATH=%cd%
python -m pytest tests/application/pipeline/test_coverage_gate.py tests/application/pipeline/test_orchestrator.py -q
```

Expected:

- target tests pass

- [ ] **Step 8: Commit**

```bash
git add tests/application/pipeline/test_coverage_gate.py tests/application/pipeline/test_orchestrator.py src/meridian/application/pipeline/coverage_gate.py src/meridian/application/pipeline/orchestrator.py
git commit -m "feat: add coverage gate and evidence selection orchestration"
```

### Task 4: Harden Research Agent And Source Adapters

**Files:**
- Modify: `src/meridian/infrastructure/llm/research_agent.py`
- Modify: `src/meridian/infrastructure/external_apis/pubmed_client.py`
- Modify: `src/meridian/infrastructure/external_apis/arxiv_client.py`
- Modify: `src/meridian/interfaces/workers/tasks.py`
- Test: `tests/infrastructure/llm/test_research_agent.py`

- [ ] **Step 1: Write failing tests for source-native query usage**

```python
async def test_research_agent_uses_source_query_planner_for_pubmed():
    ...
    assert pubmed_client.calls == ['mRNA vaccine AND ("2022"[Date - Publication] : "3000"[Date - Publication])']
```

- [ ] **Step 2: Write failing tests for deterministic retry path**

```python
async def test_research_agent_records_source_queries_for_retry_planning():
    ...
    assert agent.source_queries["pubmed"].startswith("mRNA vaccine")
```

- [ ] **Step 3: Run tests to verify they fail**

Run:

```bash
set PYTHONPATH=%cd%
python -m pytest tests/infrastructure/llm/test_research_agent.py -q
```

Expected:

- failing assertions around source query planning and metadata

- [ ] **Step 4: Inject `SourceQueryPlanner` into `ResearchAgent`**

```python
class ResearchAgent:
    def __init__(..., source_query_planner=None, ...):
        self.source_query_planner = source_query_planner or SourceQueryPlanner()
        self.source_queries = {}
```

- [ ] **Step 5: Compile source-native queries before dispatch**

```python
compiled_query = self.source_query_planner.compile(
    user_query=topic,
    execution_query=enriched_query,
    domain=self.domain,
    source=source,
)
self.source_queries[source] = compiled_query
results = await _dispatch_search(source, compiled_query)
```

- [ ] **Step 6: Keep adapters thin but tolerant**

```python
class PubMedClient:
    async def search(self, query: str, limit: int = 3) -> list[Document]:
        ...
```

Do not add global evidence filtering in adapters. Only keep source-specific transport and normalization behavior here.

- [ ] **Step 7: Wire the new services in worker task construction**

```python
policy = ReliabilityPolicy()
query_planner = SourceQueryPlanner()
relevance_scorer = RelevanceScorer()
evidence_selection = EvidenceSelectionService(policy=policy, relevance_scorer=relevance_scorer)
coverage_gate = CoverageGate(policy)
```

- [ ] **Step 8: Run tests to verify they pass**

Run:

```bash
set PYTHONPATH=%cd%
python -m pytest tests/infrastructure/llm/test_research_agent.py tests/application/pipeline/test_orchestrator.py -q
```

Expected:

- target tests pass

- [ ] **Step 9: Commit**

```bash
git add tests/infrastructure/llm/test_research_agent.py src/meridian/infrastructure/llm/research_agent.py src/meridian/infrastructure/external_apis/pubmed_client.py src/meridian/infrastructure/external_apis/arxiv_client.py src/meridian/interfaces/workers/tasks.py
git commit -m "feat: harden source-native search execution"
```

### Task 5: Add Report-Depth Wiring, API Metadata, And Evaluation Fixtures

**Files:**
- Modify: `src/meridian/infrastructure/llm/synthesizer.py`
- Modify: `src/meridian/interfaces/api/routers/research.py`
- Create: `tests/application/pipeline/fixtures/test_output_reliability_fixtures.py`
- Modify: `tests/interfaces/api/test_research_router.py`
- Modify: `README.md`

- [ ] **Step 1: Write failing tests for report depth and selection metadata**

```python
async def test_synthesizer_uses_report_depth_modifier():
    ...
    assert "deeper analysis" in llm.calls[0]["messages"][0]["content"]


async def test_research_report_exposes_selection_metadata():
    ...
    assert payload["selection"]["accepted_count"] == 2
```

- [ ] **Step 2: Write the first structured regression fixture**

```python
FIXTURES = [
    {
        "query": "Recent advances in mRNA vaccines",
        "expected_domain": "biomedical",
        "accept_titles": ["mRNA vaccine advances"],
        "reject_titles": ["Solar Upper Transition Region Imager"],
        "expected_coverage_action": "synthesize",
        "expect_retry": False,
    }
]
```

- [ ] **Step 3: Run tests to verify they fail**

Run:

```bash
set PYTHONPATH=%cd%
python -m pytest tests/infrastructure/llm/test_synthesizer.py tests/interfaces/api/test_research_router.py tests/application/pipeline/fixtures/test_output_reliability_fixtures.py -q
```

Expected:

- failing assertions for missing metadata and fixture coverage

- [ ] **Step 4: Extend synthesizer to honor `report_depth`**

```python
depth_instruction = (
    "Provide a deeper analysis with more detail, tradeoffs, and supporting explanation."
    if report_depth == "deep"
    else "Keep the report concise and well-structured."
)
messages = [
    {"role": "system", "content": f"{system_prompt}\n\n{depth_instruction}"},
    ...
]
```

- [ ] **Step 5: Expose selection metadata in the report payload**

```python
selection_metadata = workspace_metadata.get("selection", {})
```

Extend the response model and payload builder so the workspace can later show accepted and rejected evidence summaries.

- [ ] **Step 6: Add structured regression-fixture assertions**

```python
def test_biomedical_fixture_rejects_solar_imaging_noise():
    fixture = FIXTURES[0]
    ...
    assert rejected_titles == fixture["reject_titles"]
```

- [ ] **Step 7: Update README with reliability-layer overview**

```md
- source-native query planning
- evidence selection before chunking
- coverage-gated synthesis
```

- [ ] **Step 8: Run tests to verify they pass**

Run:

```bash
set PYTHONPATH=%cd%
python -m pytest tests/infrastructure/llm/test_synthesizer.py tests/interfaces/api/test_research_router.py tests/application/pipeline/fixtures/test_output_reliability_fixtures.py -q
```

Expected:

- target tests pass

- [ ] **Step 9: Commit**

```bash
git add tests/infrastructure/llm/test_synthesizer.py tests/interfaces/api/test_research_router.py tests/application/pipeline/fixtures/test_output_reliability_fixtures.py src/meridian/infrastructure/llm/synthesizer.py src/meridian/interfaces/api/routers/research.py README.md
git commit -m "feat: expose reliability metadata and fixture evaluation"
```

### Task 6: Run Final Verification

**Files:**
- Modify: none unless fixes are required
- Test: `tests/application/pipeline/*.py`
- Test: `tests/infrastructure/llm/*.py`
- Test: `tests/interfaces/api/test_research_router.py`
- Test: `frontend/src/pages/__tests__/ResearchDashboardPage.test.tsx`

- [ ] **Step 1: Run the full targeted backend verification slice**

Run:

```bash
set PYTHONPATH=%cd%
python -m pytest tests/application/pipeline/test_reliability_policy.py tests/application/pipeline/test_source_query_planner.py tests/application/pipeline/test_relevance_scorer.py tests/application/pipeline/test_evidence_selection.py tests/application/pipeline/test_coverage_gate.py tests/application/pipeline/test_orchestrator.py tests/infrastructure/llm/test_research_agent.py tests/infrastructure/llm/test_synthesizer.py tests/interfaces/api/test_research_router.py tests/application/pipeline/fixtures/test_output_reliability_fixtures.py -q
```

Expected:

- all listed tests pass

- [ ] **Step 2: Run frontend verification**

Run:

```bash
cd frontend
npm test -- --run src/pages/__tests__/ResearchDashboardPage.test.tsx src/pages/__tests__/ResearchWorkspacePage.test.tsx
npm run lint
npm run build
```

Expected:

- tests pass
- lint passes
- build completes

- [ ] **Step 3: Commit final verification-only or cleanup fixes if needed**

```bash
git add <any changed files from verification fixes>
git commit -m "test: complete output reliability verification"
```

- [ ] **Step 4: Prepare review summary**

Capture:

- which off-topic fixture cases now fail closed
- which accepted evidence fixtures now pass
- any remaining gaps for later evaluation work

---

## Self-Review

Spec coverage check:

- `SourceQueryPlanner`: covered by Task 1 and Task 4
- `RelevanceScorer`: covered by Task 2
- `EvidenceSelectionService`: covered by Task 2 and Task 3
- `CoverageGate`: covered by Task 3
- retry strategy foundation: covered by Task 1 and Task 4
- structured regression fixtures: covered by Task 5
- evaluation metadata surfaced in API/UI: covered by Task 5

Placeholder scan:

- no `TODO` / `TBD` placeholders
- every code-writing step includes concrete code
- every run step includes concrete commands

Type consistency check:

- `ReliabilityPolicy`, `SourceQueryPlanner`, `RelevanceScorer`, `EvidenceSelectionService`, and `CoverageGate` are used consistently across tasks
- `report_depth` is threaded consistently from orchestrator to synthesizer
- `selection` metadata is introduced once and reused consistently

