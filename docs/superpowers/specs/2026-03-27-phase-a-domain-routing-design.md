# Phase A Domain Routing Design

## Summary

Phase A upgrades Meridian's research entrypoint so each run classifies the query domain before searching, then exposes only the source tools that fit that domain. The design keeps the current four-layer architecture intact by adding new application services and infrastructure adapters without changing domain entities or repository protocols.

This phase uses normalized source adapters that all return `list[Document]`. That choice keeps source-specific response shapes out of the agent loop, simplifies routing, and leaves room for a future registry or plugin system without forcing a rewrite of the pipeline.

## Goals

- Classify the incoming query into one of five allowed labels: `biomedical`, `computer_science`, `economics`, `legal`, `general`
- Route the research agent to a domain-specific tool set instead of the current hard-coded tool list
- Add PubMed, IEEE, and Semantic Scholar adapters that follow the project's existing failure-tolerant pattern
- Preserve the current orchestrator contract: the agent still returns a `list[Document]`
- Keep the design compatible with a future move to a registry-driven source system

## Non-Goals

- No changes to domain entities or repository protocols in this phase
- No changes to chunking, retrieval ranking, report formatting, or query enrichment in this phase
- No frontend changes
- No plugin framework yet; this phase only introduces the seams that would support one later

## Current Constraints

- The current `ResearchAgent` constructs its own source clients internally
- Existing source clients return source-specific DTOs instead of normalized `Document` objects
- Tool schemas are hard-coded inside the agent
- Celery worker wiring is the practical composition root for this pipeline

These constraints make dynamic routing awkward today, so the main refactor in this phase is dependency injection plus source normalization.

## Recommended Approach

Use thin application services plus normalized infrastructure adapters.

This approach adds `DomainClassifier` and `SourceRouter` to the application layer, injects all search adapters into `ResearchAgent`, and makes every adapter return `Document` objects directly. It is the best fit because it:

- follows the project's clean architecture direction
- reduces branching inside the agent
- avoids duplicating per-source mapping logic
- keeps a clear path to a future registry-driven implementation

## Architecture

### New application services

#### `DomainClassifier`

Location:
- `src/meridian/application/pipeline/domain_classifier.py`

Responsibility:
- Ask the LLM to classify a research query into exactly one allowed domain label

Contract:

```python
async def classify(self, query: str) -> str
```

Behavior:
- Sends a tightly constrained system prompt to the injected OpenRouter client
- Normalizes the response with `strip()` and `lower()`
- Validates against the allowed labels
- Falls back to `general` if the response is invalid or unusable

Dependencies:
- `OpenRouterClient`

#### `SourceRouter`

Location:
- `src/meridian/application/pipeline/source_router.py`

Responsibility:
- Return the active OpenRouter-compatible tool schemas for a given domain

Contract:

```python
def get_tools_for_domain(self, domain: str) -> list[dict]
```

Behavior:
- Encodes the domain-to-tool mapping
- Builds tool schemas in one place instead of scattering them through the agent
- Returns a safe `general` tool set for unknown domains

Dependencies:
- Injected source clients for consistency and future extensibility, even if the first version only uses them indirectly

### New infrastructure adapters

Location:
- `src/meridian/infrastructure/external_apis/`

New adapters:
- `pubmed_client.py`
- `ieee_client.py`
- `semantic_scholar_client.py`

Adapter contract:

```python
async def search(self, query: str, limit: int = ...) -> list[Document]
```

Shared rules:
- Return normalized `Document` objects
- Swallow external failures and return `[]`
- Never raise integration exceptions to the caller
- Log warnings for soft-failure conditions that matter operationally

Source-specific rules:
- PubMed uses NCBI E-utilities through async `httpx`
- IEEE reads `IEEE_API_KEY` from the environment; if missing, log a warning and return `[]`
- Semantic Scholar uses the Graph API and acts as a higher-quality academic fallback than generic web search for `general` queries

### Agent refactor

Location:
- `src/meridian/infrastructure/llm/research_agent.py`

Responsibility:
- Orchestrate one research run using dynamic tools instead of a fixed tool list

The refactored agent should:
- receive its dependencies through the constructor
- classify the topic before starting tool calls
- store the chosen domain on `self.domain`
- ask `SourceRouter` for the active tool schemas
- dispatch tool calls through a table-driven or `match/case` structure
- accumulate normalized `Document` objects from all tool calls

The agent should no longer know how each source result is shaped. That conversion belongs in the adapters.

### Composition root

Location:
- `src/meridian/interfaces/workers/tasks.py`

Responsibility:
- Instantiate concrete dependencies and wire them together for the Celery task

This file should create:
- `OpenRouterClient`
- `WikipediaClient`
- `ArXivClient`
- `WebSearchClient`
- `PubMedClient`
- `IEEEClient`
- `SemanticScholarClient`
- `DomainClassifier`
- `SourceRouter`
- `ResearchAgent`
- `ReportSynthesizer`
- `PipelineOrchestrator`

## Domain Routing Rules

The routing map for Phase A is:

| Domain | Active tools |
|---|---|
| `biomedical` | `search_pubmed`, `search_arxiv`, `search_wikipedia`, `finish_research` |
| `computer_science` | `search_arxiv`, `search_ieee`, `search_web`, `finish_research` |
| `economics` | `search_semantic_scholar`, `search_web`, `search_wikipedia`, `finish_research` |
| `legal` | `search_web`, `search_wikipedia`, `finish_research` |
| `general` | `search_semantic_scholar`, `search_wikipedia`, `search_web`, `finish_research` |

This mapping stays centralized in `SourceRouter`. The orchestrator and the rest of the pipeline should not need to understand source-selection rules.

## Runtime Flow

1. Celery task builds all concrete clients and services.
2. Orchestrator calls `ResearchAgent.run(topic=job.query)`.
3. Agent calls `await DomainClassifier.classify(topic)`.
4. Agent stores the result on `self.domain`.
5. Agent calls `SourceRouter.get_tools_for_domain(self.domain)`.
6. LLM runs with the returned domain-specific tools.
7. For each tool call, the agent dispatches to one adapter method and receives normalized `Document` objects.
8. Agent appends those documents to its collected evidence set.
9. `finish_research` stops the loop.
10. Agent returns `list[Document]` to the orchestrator.

## Error Handling

Phase A should degrade gracefully.

Rules:
- Invalid classifier output falls back to `general`
- Missing `IEEE_API_KEY` logs a warning and returns `[]`
- Source API failures return `[]`
- Malformed tool-call arguments fall back to the original topic where practical
- Unknown tool names are ignored defensively and logged

The system should prefer a smaller evidence set over a failed run.

## Logging

Add operational logs at the application and integration boundaries:

- `DEBUG`: classified domain
- `DEBUG`: active tool names selected for the run
- `WARNING`: missing IEEE API key
- `WARNING`: unexpected tool name or unrecoverable tool argument issue

Logging should support diagnosis without exposing the rest of the pipeline to adapter-specific details.

## Testing Strategy

### Unit tests

- `DomainClassifier` returns valid labels and falls back to `general` on invalid LLM output
- `SourceRouter` returns the expected tool names for each domain
- `ResearchAgent` selects the routed tool list and dispatches each tool to the correct adapter
- `ResearchAgent` stores `self.domain` after classification

### Adapter tests

- PubMed adapter converts successful API responses into `Document` objects
- IEEE adapter returns `[]` and logs a warning when `IEEE_API_KEY` is missing
- Semantic Scholar adapter converts successful API responses into `Document` objects
- All adapters return `[]` on network or parsing failures

### Integration smoke test

- Worker wiring assembles the new dependency graph without constructor mismatches

This phase does not need full end-to-end tests against live external services.

## Migration Path Toward a Registry System

This design intentionally keeps the future pivot to a richer source registry cheap.

To preserve that option:
- adapters all share the same `search() -> list[Document]` contract
- tool schema construction lives in one place
- routing rules live in one place
- agent dispatch is table-driven rather than hard-coded in multiple branches across the codebase

If Meridian later moves to a registry or plugin model, the likely change is replacing `SourceRouter` and the dispatch table with richer source definitions. The orchestrator contract and downstream pipeline can remain the same.

## Acceptance Criteria

Phase A is complete when:
- the agent classifies each query into a valid domain label
- the active tool list is domain-specific
- the new academic and biomedical adapters are wired into the worker
- all search adapters return normalized `Document` objects
- the pipeline still completes successfully when optional sources are unavailable
- the design remains compatible with later phases without requiring domain-layer changes
