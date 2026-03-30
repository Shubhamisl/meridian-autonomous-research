# Meridian Output Reliability Design

## Goal

Improve Meridian from a pipeline that can retrieve and synthesize plausible-but-noisy evidence into a system that produces system-wide, cross-domain reliable outputs.

The target is not another retrieval hotfix. The target is a stronger evidence engine:

- source-native query construction
- explicit evidence selection before chunking
- off-topic rejection before retrieval and synthesis
- diversity-aware evidence acceptance
- guarded synthesis when coverage is insufficient
- evaluation-driven quality measurement across domains

This design optimizes for:

- biomedical
- computer science
- economics
- legal
- general

using one consistent quality architecture rather than one-off domain patches.

## Current Reliability Problems

Meridian’s output quality currently degrades for a simple reason: it trusts candidate results too early.

Today the high-level flow is:

1. classify query
2. route sources
3. search and collect raw `Document`s
4. chunk all collected documents
5. retrieve from Chroma
6. synthesize

This causes five reliability failures:

### 1. Query-language mismatch

`QueryProcessor` enriches queries with operator syntax such as `after:2022-01-01` and quoted phrases, but source adapters like PubMed and arXiv do not interpret all of that syntax reliably.

Result:

- malformed or weak academic queries
- noisy recall
- results that are "top-ranked" by the source but not actually relevant to the user’s topic

### 2. No topical relevance gate

Search adapters return results and Meridian treats them as valid evidence immediately.

Result:

- irrelevant PubMed papers
- irrelevant arXiv papers
- tangential or noisy web results
- weak candidates entering chunking and retrieval

### 3. No evidence diversity policy

Meridian optimizes for "enough documents to continue" rather than "best evidence set for synthesis."

Result:

- too many results from a single source family
- poor balance between primary and secondary sources
- brittle synthesis when evidence is narrow or repetitive

### 4. Retrieval cannot fix a polluted evidence set

Weighted Chroma retrieval only reorders chunks already saved. If bad evidence enters the vector store, retrieval still operates on a contaminated pool.

Result:

- better ranking, but not better evidence

### 5. No coverage gate before synthesis

The orchestrator synthesizes as long as the pipeline reaches the end, even when accepted evidence may not truly cover the query.

Result:

- confident reports with weak grounding
- topic drift between user request and returned report

## Recommended Approach

### Approach 1: Evidence-quality layer before chunking

Introduce a new application-layer evidence curation stage between search and chunking.

This stage will:

- normalize source-native query behavior
- score candidate topical relevance
- deduplicate near-identical results
- enforce diversity and source-balance rules
- reject low-signal evidence before chunking
- gate synthesis on coverage quality

This is the recommended approach because it improves all domains and all source adapters instead of chasing individual failure cases.

### Approach 2: Source-by-source hardening only

Improve PubMed, arXiv, web, and legal search behavior individually.

This is useful but insufficient on its own because bad candidates can still leak through from any source unless there is a shared acceptance layer.

### Approach 3: Stronger models without retrieval redesign

Use better LLMs for agent planning and synthesis.

This may improve behavior somewhat, but it does not solve the core problem: synthesis quality is bounded by evidence quality.

### Recommendation

Use Approach 1, with source-specific hardening as part of that design.

## Architecture

Add four new reliability-oriented components.

### 1. SourceQueryPlanner

Location:

- `src/meridian/application/pipeline/source_query_planner.py`

Responsibility:

- compile the user query into source-native query strings
- avoid leaking unsupported operator syntax into sources that do not use it
- preserve the separation between:
  - display query
  - execution query
  - source-native query

Examples:

- PubMed should use PubMed-native date and phrase conventions
- arXiv should prefer phrase-based academic search without fake field syntax
- web should retain exclusion operators and source exclusions
- legal and economics web searches can bias toward institutional or high-trust domains

This replaces the current one-size-fits-all enrichment strategy with source-aware compilation.

### 2. RelevanceScorer

Location:

- `src/meridian/application/pipeline/relevance_scorer.py`

Responsibility:

- score whether a candidate `Document` is actually relevant to the user’s original request
- return a normalized topical relevance score between `0.0` and `1.0`

Recommended scoring strategy:

1. lexical alignment
2. embedding similarity
3. optional LLM adjudication for ambiguous borderline cases only

The LLM should not score every document. It should be reserved for:

- borderline cases
- source disagreement
- very short or noisy metadata-only results

Threshold policy:

- base automatic reject: `< 0.45`
- borderline band: `0.45 <= score < 0.70`
- base automatic accept: `>= 0.70`
- final minimum accepted relevance after adjudication: `0.60`

These per-document thresholds should be fixed across domains in v1. Domain differences should be expressed through coverage requirements rather than by making document-level acceptance harder to reason about.

LLM adjudication budget:

- maximum `5` candidate documents per request
- adjudication only for borderline candidates after deduplication
- if adjudication times out or fails, fall back to the non-LLM score
- a borderline candidate with failed adjudication remains rejected unless its non-LLM score independently clears the automatic accept threshold

### 3. EvidenceSelectionService

Location:

- `src/meridian/application/pipeline/evidence_selection.py`

Responsibility:

- accept raw candidate `Document`s from the agent
- deduplicate and cluster similar documents
- apply relevance scoring
- enforce source diversity
- select the final accepted evidence set
- produce structured selection metadata

Outputs should include:

- accepted documents
- rejected documents
- acceptance reason
- rejection reason
- per-document relevance score
- source-native query provenance

This service becomes the quality gate before chunking.

Decomposition:

- `EvidenceSelectionService` should be a facade with one public method, for example:
  - `select(query, domain, candidates, source_queries) -> EvidenceSelectionResult`
- internally it should orchestrate smaller focused collaborators:
  - `CandidateDeduplicator`
  - `RelevanceScorer`
  - `DiversitySelector`
  - selection metadata assembly

Execution order:

1. normalize and deduplicate candidates
2. apply lightweight source sanity checks
3. score relevance
4. send only borderline candidates to LLM adjudication
5. apply diversity selection and source-balance rules
6. build accepted/rejected outputs with reasons

Deduplication must happen before relevance scoring so Meridian does not waste compute scoring multiple near-identical candidates.

Call pattern:

- the orchestrator should call one facade method on `EvidenceSelectionService`
- the orchestrator should not manually step through sub-stages
- internal collaborators should stay unit-testable in isolation

### 4. CoverageGate

Location:

- `src/meridian/application/pipeline/coverage_gate.py`

Responsibility:

- determine whether the accepted evidence set is sufficient to synthesize a report

Coverage should consider:

- topical completeness
- evidence count
- source diversity
- domain-specific sufficiency

Coverage thresholds:

- `biomedical`: minimum `3` accepted documents, minimum `2` distinct sources, minimum accepted-set average relevance `0.70`
- `computer_science`: minimum `3` accepted documents, minimum `2` distinct sources, minimum accepted-set average relevance `0.68`
- `economics`: minimum `3` accepted documents, minimum `2` distinct sources, minimum accepted-set average relevance `0.68`
- `legal`: minimum `3` accepted documents, minimum `2` distinct sources, minimum accepted-set average relevance `0.70`
- `general`: minimum `2` accepted documents, minimum `1` distinct source, minimum accepted-set average relevance `0.65`

Source diversity in v1 should be operationalized as:

- minimum distinct source count by domain
- no single source contributing more than `60%` of accepted documents when more than one source is available
- at most `2` near-duplicate accepted documents from the same source/query family

Threshold ownership:

- thresholds should be configuration-driven, not hardcoded inline
- introduce an injectable `ReliabilityPolicy` or `EvidencePolicy` settings object in the application layer
- the values above are the default production policy for v1
- learned thresholds are explicitly out of scope for this iteration

If coverage is insufficient, the orchestrator should:

- retry with a narrower or more focused search plan, or
- fail with a precise "insufficient relevant evidence" reason

It must not silently synthesize weak output.

Retry policy:

- maximum retry count: `1`
- the retry happens inside the background job, so from the user's perspective it is asynchronous and remains part of the same workspace run
- after one failed retry, Meridian must fail with a precise quality message rather than continue searching indefinitely

Retry plan generation:

- v1 should use a deterministic narrowing strategy, not free-form agent replanning
- `SourceQueryPlanner` should provide a refinement method that uses:
  - original user query
  - domain
  - source-native queries attempted
  - rejection reasons from `EvidenceSelectionService`
- the refinement strategy should:
  - preserve the same domain
  - narrow the query around the strongest intent terms
  - drop unsupported or noisy query fragments
  - prune sources that returned only rejected evidence when appropriate

Retry can change:

- source-native query strings
- source subset

Retry should not change:

- display query
- classified domain

## Data Flow

The upgraded flow becomes:

1. user submits query
2. `DomainClassifier` identifies the domain
3. `SourceRouter` selects the eligible sources
4. `SourceQueryPlanner` compiles source-native queries
5. `ResearchAgent` gathers raw candidate `Document`s
6. `EvidenceSelectionService`:
   - deduplicates
   - scores topical relevance
   - ranks diversity
   - rejects low-quality evidence
7. accepted evidence only moves into chunking
8. `CoverageGate` decides whether synthesis is allowed
9. if coverage is insufficient:
   - retry with tighter search, or
   - fail clearly
10. if coverage is sufficient:
   - chunk
   - retrieve
   - synthesize

This creates a strong invariant:

> synthesis only sees evidence that already passed relevance and coverage acceptance.

## Component Responsibilities

### ResearchAgent

Keep the agent responsible for:

- deciding which tools to call
- gathering raw candidates
- recording query provenance

Do not make it responsible for final evidence quality decisions. That belongs in the new application-layer evidence selection stage.

### Source Adapters

Keep source adapters narrow:

- fetch source results
- normalize to `Document`
- return `[]` on failure

Do not embed global evidence policy into adapters. Source-specific syntax handling is acceptable, but final relevance acceptance belongs outside adapters.

### Orchestrator

The orchestrator should gain a new phase between research and chunking:

- `research`
- `select_evidence`
- `chunk`
- `retrieve`
- `synthesize`

The orchestrator should also persist quality metadata for the workspace UI and debugging surfaces.

### Chroma Repository

The vector store remains valuable, but only after the evidence pool is filtered. Weighted retrieval stays useful, but the repository should not be treated as the first line of defense against topic drift.

## Quality Policy

### Query policy

- never inject unsupported operator syntax blindly into academic queries
- compile each source query separately
- preserve original user intent terms
- retain execution-query provenance in metadata

### Evidence admission policy

A document should only be accepted if it passes:

- source parse success
- minimum topical relevance
- duplicate suppression
- diversity checks

Documents that fail should be retained in metadata for debugging, but must not enter chunking.

### Diversity policy

Accepted evidence should avoid collapsing into one source family.

Recommended default behavior:

- prefer at least two complementary sources when feasible
- cap near-duplicate documents
- avoid overfilling with weak academic results just because the source returned them

### Coverage policy

If accepted evidence is too narrow or too weak:

- do not synthesize
- either retry or fail with an explicit quality message

### Explainability policy

Store:

- source-native query used
- relevance score
- credibility score
- acceptance/rejection reason

This should later surface in the workspace so users can understand why evidence was selected.

## Testing Strategy

This work should not be validated by unit tests alone. Output reliability must be evaluated as a system property.

### 1. Unit tests

Add focused tests for:

- source-native query compilation
- relevance scoring
- deduplication logic
- diversity constraints
- coverage gate outcomes

### 2. Regression fixtures

Create a benchmark set of known-bad and known-ambiguous prompts such as:

- mRNA vaccine recent advances
- cancer treatment advances
- legal-bias queries
- AI regulation in the EU
- cybersecurity threat reports

For each fixture, assert:

- obviously off-topic documents are rejected
- accepted evidence remains on-topic
- synthesis is blocked when evidence is inadequate

Each regression fixture must be structured, not just named. Every fixture definition should include:

- input query
- expected domain
- expected source families allowed or preferred
- example candidate documents that should be accepted
- example candidate documents that should be rejected
- expected minimum accepted evidence count
- expected coverage verdict
- whether retry is expected
- whether synthesis should proceed or fail

This turns the fixture set into a true regression contract rather than a loose benchmark list.

### 3. Evaluation harness

Add an evaluation workflow that scores:

- evidence topical relevance
- evidence diversity
- source appropriateness by domain
- mismatch rate between query and accepted evidence
- final report grounding quality

This benchmark should span:

- biomedical
- legal
- economics
- computer science
- general

### 4. Workspace verification

Once evidence selection metadata exists, validate that the frontend explainability panel reflects:

- accepted evidence
- rejected evidence counts or summaries
- source queries
- reasons for insufficient evidence failures

## Implementation Priorities

Recommended order:

1. `SourceQueryPlanner`
2. `RelevanceScorer`
3. `EvidenceSelectionService`
4. `CoverageGate`
5. orchestrator integration
6. evaluation benchmark set
7. UI explainability extensions

This order improves actual output quality first, then observability.

## Out of Scope

The following are not part of this design:

- deployment architecture changes
- frontend redesign
- persistence engine migration away from SQLite
- replacing OpenRouter with another provider
- broad rework of the domain layer

## Success Criteria

This project is successful when:

- bad PubMed/arXiv/web results are rejected before chunking
- accepted evidence sets are materially more on-topic across all domains
- weak evidence no longer silently produces polished but misleading reports
- quality can be measured through repeatable evaluation fixtures
- workspace explainability can show why evidence was accepted
