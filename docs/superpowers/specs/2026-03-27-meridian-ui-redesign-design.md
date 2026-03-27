# Meridian UI Redesign Design

## Goal
Replace the current masonry-style research dashboard with a calmer, more premium product experience that matches Meridian's upgraded intelligence pipeline. The new UI should present Meridian as a guided research copilot with hidden complexity, while still exposing source quality, explainability, and progress when the user wants it.

## Product Direction
Meridian should move from a thin job launcher into a research workspace. The product model is:
- **Dashboard** for starting work and re-entering previous runs
- **Detail workspace** for reading, trusting, and inspecting a completed or running report

The target audience spans analysts, executives, investigators, and general knowledge workers, so the default UI must remain accessible while preserving depth for serious review.

## Existing Frontend Context
The current frontend already exists in `frontend/` as a Vite + React application with authenticated routing. The primary route is a masonry dashboard and a report viewer. The redesign should replace that visual and information architecture rather than introducing a separate product shell.

Relevant existing surfaces:
- `frontend/src/pages/MasonryDashboard.tsx`
- `frontend/src/components/ReportViewer.tsx`
- `frontend/src/components/ResearchCard.tsx`
- `frontend/src/components/Navbar.tsx`

## Core Experience Principles
- Show the answer first.
- Keep technical complexity hidden by default.
- Make trust inspectable through evidence, citations, provenance, and readable progress.
- Use editorial readability over dense dashboarding.
- Avoid generic AI-product aesthetics and purple-glow styling.

## Screen Model

### 1. Dashboard
The dashboard should have four primary zones:
- **Research composer:** a single prominent natural-language input with one clear CTA
- **Starter modes:** lightweight cards for common research intents across supported domains
- **Recent runs:** elegant cards showing title, status, domain, and recency
- **Trust band:** simple statements translating backend intelligence into user language

The dashboard should feel calm and intentional, not busy or over-optimized. It should emphasize one primary action: start research.

### 2. Research Detail Workspace
The detail workspace should be report-first and reading-centric.

Primary areas:
- **Header:** title, status, detected domain, selected report format, job metadata
- **Executive summary:** prominent summary or abstract module
- **Main report:** long-form report content with strong typography and citation anchors
- **Explainability panel:** domain routing, format selection, credibility weighting, query refinement
- **Evidence section:** source cards with provenance, snippets, credibility, relevance
- **Pipeline timeline:** classify, collect, score, chunk, retrieve, synthesize

The default state should emphasize the report itself. Evidence and mechanics should be secondary but easy to inspect.

### 3. Mobile Detail Variant
Mobile should not be a compressed desktop dashboard. It should prioritize:
- summary first
- readable report layout
- accordion or bottom-sheet explainability
- stacked evidence cards
- compact pipeline status

## Mapping Phase A-D Intelligence Into UI
The redesign should visibly support the new backend behavior:

- **Phase A:** show detected domain and active source family
- **Phase B:** surface credibility-weighted evidence and source trust cues
- **Phase C:** show chosen report format and shape the report reading experience accordingly
- **Phase D:** expose query refinement examples in explainability layers

These capabilities should be visible, but not intrusive.

## Visual Direction
- Premium editorial intelligence product
- Calm, high-trust, low-noise
- Serif-led report typography plus a clean grotesk UI sans
- Deep navy, ivory, teal, amber, and disciplined neutral surfaces
- Soft radius, layered cards, subtle elevation, precise borders
- Minimal motion used for progress and disclosure

## Stitch Deliverables
Create a `.stitch` workspace under `frontend/` with:
- `.stitch/DESIGN.md` as the visual source of truth
- prompt files for:
  - dashboard
  - detail workspace
  - mobile detail variant

These prompts should be used once Stitch MCP authentication is configured.

## Stitch Blocker
The Stitch extension is installed in Gemini CLI on this machine, but the remote Stitch MCP server is disconnected because authentication is not configured yet. The shortest path is API key authentication from `stitch.withgoogle.com`, after which the prompt package can be used directly.

## Success Criteria
- The UI clearly feels like a new product generation, not a skin on the current masonry layout.
- The dashboard makes starting research feel easy and premium.
- The detail page makes the final report feel authoritative and readable.
- Explainability and evidence are accessible without cluttering the main flow.
- The design system is explicit enough to guide future implementation in the existing React app.
