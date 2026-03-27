# Meridian UI Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current masonry-style frontend with a guided dashboard plus dedicated research workspace that matches the approved Meridian UI redesign and existing API capabilities.

**Architecture:** Keep the existing Vite + React app and authenticated shell, but replace the current page model with a dashboard route and a research detail route. Use the Stitch design system and generated HTML as reference for layout, typography, tokens, and composition, while gracefully degrading unsupported metadata until the backend exposes richer fields.

**Tech Stack:** React 19, TypeScript, Vite, Tailwind CSS, Framer Motion, React Router, Firebase Auth

---

## File Structure

- Modify: `frontend/src/App.tsx`
  - Replace the single-dashboard route model with dashboard + detail routes.
- Create: `frontend/src/lib/api.ts`
  - Centralize authenticated fetch helpers and frontend API types.
- Create: `frontend/src/lib/research-status.ts`
  - Shared status labels, color tokens, and lightweight formatting helpers.
- Create: `frontend/src/components/layout/AppShell.tsx`
  - Shared top bar / shell wrapper for authenticated screens.
- Create: `frontend/src/components/dashboard/ResearchComposer.tsx`
  - Hero composer matching the new guided dashboard.
- Create: `frontend/src/components/dashboard/StarterModes.tsx`
  - Guided framework cards.
- Create: `frontend/src/components/dashboard/RecentResearchList.tsx`
  - Structured list/cards replacing masonry layout.
- Create: `frontend/src/components/detail/ReportHeader.tsx`
  - Workspace header with query, status, and available metadata.
- Create: `frontend/src/components/detail/PipelineTimeline.tsx`
  - Static-but-polished phase timeline.
- Create: `frontend/src/components/detail/ExplainabilityPanel.tsx`
  - Progressive disclosure panel with graceful placeholders until richer API data exists.
- Create: `frontend/src/components/detail/EvidencePlaceholder.tsx`
  - Honest placeholder section for evidence/explainability that current API cannot yet hydrate.
- Modify: `frontend/src/components/ReportViewer.tsx`
  - Rework into the new editorial report body presentation, or split if needed.
- Create: `frontend/src/pages/ResearchDashboardPage.tsx`
  - Main dashboard page replacing masonry experience.
- Create: `frontend/src/pages/ResearchWorkspacePage.tsx`
  - Dedicated report/detail route replacing in-page modal/back-button behavior.
- Modify: `frontend/src/pages/LoginPage.tsx`
  - Align login styling with the new visual system.
- Modify: `frontend/src/index.css`
  - Replace current purple glass theme with Meridian editorial tokens and utilities.
- Modify: `frontend/tailwind.config.js`
  - Update colors, fonts, shadows, and utility tokens for the new design language.
- Remove or stop using:
  - `frontend/src/pages/MasonryDashboard.tsx`
  - `frontend/src/components/Navbar.tsx`
  - `frontend/src/components/ResearchCard.tsx`
  - `react-masonry-css` usage in the main flow

## Task 1: Lock The New Visual System

**Files:**
- Modify: `frontend/tailwind.config.js`
- Modify: `frontend/src/index.css`
- Modify: `frontend/src/pages/LoginPage.tsx`

- [ ] **Step 1: Write the failing visual-shell verification step**

Run: `npm run build`
Expected: PASS before changes so we know the current frontend baseline is clean enough to refactor.

- [ ] **Step 2: Update Tailwind tokens to the Meridian design system**

```js
/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Manrope"', "sans-serif"],
        serif: ['"Newsreader"', "serif"],
      },
      colors: {
        ink: "#0F172A",
        slate: "#1E293B",
        ivory: "#F8FAFC",
        paper: "#F6F1E8",
        teal: "#0F766E",
        "teal-soft": "#CCFBF1",
        amber: "#D97706",
        blue: "#2563EB",
        fog: "#CBD5E1",
        rose: "#B91C1C",
      },
      boxShadow: {
        panel: "0 18px 48px rgba(15, 23, 42, 0.08)",
        soft: "0 10px 30px rgba(15, 23, 42, 0.06)",
      },
      borderRadius: {
        xl: "1rem",
        "2xl": "1.5rem",
      },
    },
  },
  plugins: [require("@tailwindcss/typography")],
}
```

- [ ] **Step 3: Replace `index.css` theme utilities with Meridian editorial utilities**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&family=Newsreader:opsz,wght@6..72,300..800&display=swap');

@layer base {
  :root {
    color: #0f172a;
    background: #f8fafc;
  }

  body {
    @apply min-h-screen bg-ivory text-ink antialiased;
    background-image:
      radial-gradient(circle at top left, rgba(15, 118, 110, 0.08), transparent 28%),
      linear-gradient(to bottom, rgba(255,255,255,0.96), rgba(248,250,252,1));
  }

  #root {
    @apply min-h-screen;
  }
}

@layer components {
  .editorial-panel {
    @apply rounded-2xl border border-fog/60 bg-white/85 shadow-panel backdrop-blur-sm;
  }

  .editorial-muted {
    @apply text-sm text-slate/70;
  }

  .status-pill {
    @apply inline-flex items-center gap-2 rounded-full px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.16em];
  }

  .section-label {
    @apply text-[11px] font-semibold uppercase tracking-[0.22em] text-teal;
  }

  .report-prose {
    @apply prose prose-slate max-w-none prose-headings:font-serif prose-headings:text-ink prose-p:text-slate/90 prose-strong:text-ink;
  }
}
```

- [ ] **Step 4: Refresh the login page to match the new visual system**

```tsx
// Keep the same auth behavior, but restyle around the new editorial palette,
// serif logotype, light canvas, and restrained accent treatment.
```

- [ ] **Step 5: Run the frontend build**

Run: `npm run build`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add frontend/tailwind.config.js frontend/src/index.css frontend/src/pages/LoginPage.tsx
git commit -m "feat: establish meridian editorial frontend theme"
```

## Task 2: Replace The Dashboard Experience

**Files:**
- Create: `frontend/src/lib/api.ts`
- Create: `frontend/src/lib/research-status.ts`
- Create: `frontend/src/components/layout/AppShell.tsx`
- Create: `frontend/src/components/dashboard/ResearchComposer.tsx`
- Create: `frontend/src/components/dashboard/StarterModes.tsx`
- Create: `frontend/src/components/dashboard/RecentResearchList.tsx`
- Create: `frontend/src/pages/ResearchDashboardPage.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Write the minimal data-flow test via manual build target**

Run: `npm run build`
Expected: PASS before replacing routes/components

- [ ] **Step 2: Add a shared authenticated API helper**

```ts
export interface ResearchJobSummary {
  id: string;
  status: string;
  query?: string;
}

export interface ResearchReport {
  id: string;
  job_id: string;
  query: string;
  markdown_content: string;
}
```

```ts
export async function authFetch(
  getToken: () => Promise<string | null>,
  url: string,
  opts: RequestInit = {},
) {
  const token = await getToken();
  return fetch(url, {
    ...opts,
    headers: {
      ...(opts.headers as Record<string, string> | undefined),
      Authorization: token ? `Bearer ${token}` : "",
    },
  });
}
```

- [ ] **Step 3: Create the new dashboard primitives**

```tsx
// ResearchComposer:
// - large textarea/input
// - start research CTA
// - advanced-parameters affordance (non-functional disclosure stub is fine)

// StarterModes:
// - four or five guided cards from the design package

// RecentResearchList:
// - structured rows/cards instead of masonry
// - use status helper tokens
```

- [ ] **Step 4: Build `ResearchDashboardPage.tsx`**

```tsx
// Responsibilities:
// - fetch jobs on load/poll
// - submit new research jobs
// - render composer, starter modes, trust band, recent runs
// - navigate to /research/:jobId when a row is selected
```

- [ ] **Step 5: Switch app routing away from `MasonryDashboard`**

```tsx
<Route
  path="/dashboard"
  element={
    <ProtectedRoute>
      <ResearchDashboardPage />
    </ProtectedRoute>
  }
/>
```

- [ ] **Step 6: Run the frontend build**

Run: `npm run build`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add frontend/src/App.tsx frontend/src/lib/api.ts frontend/src/lib/research-status.ts frontend/src/components/layout/AppShell.tsx frontend/src/components/dashboard frontend/src/pages/ResearchDashboardPage.tsx
git commit -m "feat: replace masonry dashboard with research dashboard"
```

## Task 3: Add A Dedicated Research Workspace Route

**Files:**
- Create: `frontend/src/components/detail/ReportHeader.tsx`
- Create: `frontend/src/components/detail/PipelineTimeline.tsx`
- Create: `frontend/src/components/detail/ExplainabilityPanel.tsx`
- Create: `frontend/src/components/detail/EvidencePlaceholder.tsx`
- Create: `frontend/src/pages/ResearchWorkspacePage.tsx`
- Modify: `frontend/src/components/ReportViewer.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Write the route-level verification step**

Run: `npm run build`
Expected: PASS before adding the new detail route

- [ ] **Step 2: Create the report workspace components**

```tsx
// ReportHeader:
// - query title
// - status pill
// - available metadata pills (domain/format as "Autodetected" placeholders only if API data absent)

// PipelineTimeline:
// - static six-phase timeline with styling based on current job status

// ExplainabilityPanel:
// - summarize current UI-known facts honestly
// - do not fabricate unavailable backend metadata

// EvidencePlaceholder:
// - explain that richer source/evidence cards appear when evidence metadata is available from the API
```

- [ ] **Step 3: Rework `ReportViewer` into editorial report rendering**

```tsx
// Keep markdown rendering, but move to:
// - warm paper-like reading surface
// - premium serif heading rhythm
// - cleaner export/share action area
```

- [ ] **Step 4: Build `ResearchWorkspacePage.tsx`**

```tsx
// Responsibilities:
// - read :jobId from router
// - fetch job status
// - fetch report when available
// - show running / completed / failed states
// - render report-first workspace with side panel + timeline
```

- [ ] **Step 5: Add the dedicated route**

```tsx
<Route
  path="/research/:jobId"
  element={
    <ProtectedRoute>
      <ResearchWorkspacePage />
    </ProtectedRoute>
  }
/>
```

- [ ] **Step 6: Run the frontend build**

Run: `npm run build`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/detail frontend/src/components/ReportViewer.tsx frontend/src/pages/ResearchWorkspacePage.tsx frontend/src/App.tsx
git commit -m "feat: add meridian research workspace route"
```

## Task 4: Remove Old Dashboard Assumptions And Polish Integration

**Files:**
- Modify: `frontend/src/pages/MasonryDashboard.tsx` or delete if unused
- Modify: `frontend/src/components/Navbar.tsx` or delete if unused
- Modify: `frontend/src/components/ResearchCard.tsx` or delete if unused
- Modify: `frontend/package.json` only if dependency cleanup is needed

- [ ] **Step 1: Remove or stop importing obsolete masonry components**

```tsx
// Delete dead imports/usages of:
// - react-masonry-css
// - Navbar
// - ResearchCard
// - selectedReport modal behavior
```

- [ ] **Step 2: Only remove `react-masonry-css` if no longer referenced**

Run: `npm run build`
Expected: PASS before dependency cleanup

- [ ] **Step 3: Remove dead dependency if unused**

```bash
npm uninstall react-masonry-css
```

- [ ] **Step 4: Run final verification**

Run: `npm run build`
Expected: PASS

Run: `npm run lint`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src frontend/package.json frontend/package-lock.json
git commit -m "refactor: remove old meridian dashboard scaffolding"
```

## Self-Review Checklist

- Spec coverage:
  - dashboard + detail workspace are covered in Tasks 2 and 3
  - Meridian design system adoption is covered in Task 1
  - mobile-specific styling is handled responsively inside the same page architecture
  - unsupported backend metadata is handled honestly rather than fabricated
- Placeholder scan:
  - no TODO/TBD markers remain in the plan
  - every task has exact files and verification commands
- Type consistency:
  - `ResearchJobSummary` and `ResearchReport` are defined centrally
  - the app route model consistently uses `/dashboard` and `/research/:jobId`
