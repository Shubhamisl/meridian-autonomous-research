# Design System: Meridian Research Workspace
**Project:** Meridian Frontend
**Surface:** Authenticated React web application

## 1. Visual Theme & Atmosphere
Meridian should feel like a premium research publication fused with a trustworthy AI copilot. The product tone is calm, rigorous, and authoritative rather than playful or futuristic. The interface should communicate serious analytical work across biomedical, computer science, economics, legal, and general research contexts.

The visual language should favor editorial clarity over dense dashboard chrome. Use generous whitespace, strong reading hierarchy, refined dividers, and layered panels that feel deliberate rather than ornamental. Motion should be restrained and informative, mainly for progress, panel reveals, and state transitions.

## 2. Color Palette & Roles
- **Deep Ink** (#0F172A): Primary structure color for navigation, headers, major labels, and dense UI anchors.
- **Midnight Slate** (#1E293B): Secondary structural color for cards, side panels, and elevated surfaces.
- **Cloud Ivory** (#F8FAFC): Primary application canvas and reading background.
- **Paper Warmth** (#F6F1E8): Alternate report-reading surface for premium editorial sections.
- **Signal Teal** (#0F766E): Primary action color for research submission, active states, and intelligence affordances.
- **Soft Teal Mist** (#CCFBF1): Gentle highlight background for active chips and explainability callouts.
- **Progress Amber** (#D97706): In-progress pipeline states, warm emphasis, and cautionary attention.
- **Evidence Blue** (#2563EB): Citation anchors, supporting links, and evidence navigation.
- **Muted Rose** (#B91C1C): Failure, interrupted jobs, and destructive messaging.
- **Fog Border** (#CBD5E1): Subtle separators and low-contrast outlines.

## 3. Typography Rules
- **Display / Report Headlines:** Use a high-contrast editorial serif such as Playfair Display, Cormorant Garamond, or Source Serif 4. Reserve for report titles, summary headers, and major reading moments.
- **Interface / Body:** Use a clean grotesk sans such as Manrope, Plus Jakarta Sans, or Inter Tight for navigation, metadata, controls, and dense UI text.
- **Hierarchy:** Large serif headlines should establish authority, while sans-serif metadata and controls keep the workspace efficient.
- **Reading comfort:** Report content should use wider line height, generous paragraph spacing, and clear heading rhythm to support long-form analysis.

## 4. Component Stylings
- **Primary Buttons:** Soft-rounded rectangles, medium weight, strong contrast, teal-forward actions, subtle elevation on hover.
- **Secondary Buttons:** Low-chrome buttons with strong border discipline and refined hover tinting.
- **Cards:** Large-radius containers with subtle border and light elevation. Card surfaces should feel layered, not glossy.
- **Metadata Pills:** Compact rounded pills for domain, format, status, and source tags. Use low-saturation fills and crisp labels.
- **Evidence Cards:** Structured cards with source badge, title, short snippet, credibility score, relevance indicator, and open-link action.
- **Explainability Panel:** Right-side contextual panel or drawer with compact sections, muted labels, and progressive disclosure.
- **Timeline / Pipeline Rail:** Elegant horizontal or vertical phase indicator with warm running state and teal completed state.

## 5. Layout Principles
- Favor a dashboard-plus-workspace product model over a single chat surface.
- The dashboard should emphasize one main action: start research.
- The detail page should be report-first, with secondary evidence and explainability layers available but not dominant.
- Use a broad desktop canvas with a primary reading column and a secondary context column.
- Mobile layouts should prioritize summary, report readability, and bottom-sheet access to advanced details.

## 6. Product-Specific UX Rules
- Complexity stays hidden by default but must always be discoverable.
- Show the answer first, then the evidence, then the mechanics.
- Pipeline intelligence should be translated into human-readable progress, not raw technical logs.
- Trust must be visible through citations, credibility badges, source provenance, and clear state handling.
- Avoid generic AI tropes: no purple glow-heavy styling, no hacker-console metaphors, no novelty-first animations.

## 7. Screen Targets
- **Dashboard:** Research composer, starter prompts, recent jobs, trust band.
- **Research Detail Workspace:** Report header, executive summary, long-form report, evidence panel, explainability panel, pipeline timeline.
- **Mobile Detail Variant:** Reading-first mobile screen with compact header, summary, accordions, and stacked evidence cards.
