import { ArrowRight, SlidersHorizontal } from 'lucide-react';
import type { ResearchMode } from '../../lib/research-modes';

export interface AdvancedResearchOptions {
  recentOnly: boolean;
  requireMultipleSources: boolean;
  reportDepth: 'standard' | 'deep';
}

interface ResearchComposerProps {
  query: string;
  loading: boolean;
  activeMode: ResearchMode;
  advancedOpen: boolean;
  options: AdvancedResearchOptions;
  onQueryChange: (value: string) => void;
  onToggleAdvanced: () => void;
  onOptionsChange: (options: AdvancedResearchOptions) => void;
  onSubmit: () => void;
}

export default function ResearchComposer({
  query,
  loading,
  activeMode,
  advancedOpen,
  options,
  onQueryChange,
  onToggleAdvanced,
  onOptionsChange,
  onSubmit,
}: ResearchComposerProps) {
  return (
    <section className="mb-16">
      <h1 className="max-w-4xl font-serif text-5xl font-semibold tracking-tight text-ink md:text-6xl">
        What would you like Meridian to research today?
      </h1>
      <p className="mt-5 max-w-3xl text-lg leading-8 text-slate/75">
        Meridian classifies the domain, routes the strongest sources, scores evidence credibility,
        and synthesizes a polished report so you can move from question to insight without staring
        at a pile of tabs.
      </p>

      <div className="editorial-panel mt-10 overflow-hidden">
        <textarea
          className="min-h-[176px] w-full resize-none border-0 bg-transparent px-7 py-7 font-serif text-2xl leading-relaxed text-ink placeholder:text-slate/35 focus:outline-none focus:ring-0"
          placeholder="Describe your research objective in natural language..."
          value={query}
          onChange={(event) => onQueryChange(event.target.value)}
        />
        <div className="flex flex-col gap-4 border-t border-fog/60 px-6 py-5 sm:flex-row sm:items-center sm:justify-between">
          <button
            className="inline-flex items-center gap-2 text-sm font-medium text-teal transition hover:text-ink"
            onClick={onToggleAdvanced}
            type="button"
          >
            <SlidersHorizontal className="h-4 w-4" />
            <span>{advancedOpen ? 'Hide Advanced Parameters' : 'Advanced Parameters'}</span>
          </button>
          <button
            className="inline-flex items-center justify-center gap-2 rounded-2xl bg-teal px-6 py-3 text-sm font-semibold text-white shadow-soft transition hover:bg-teal/90 disabled:cursor-not-allowed disabled:opacity-50"
            disabled={!query.trim() || loading}
            onClick={onSubmit}
          >
            <span>{loading ? 'Preparing research…' : 'Start Research'}</span>
            <ArrowRight className="h-4 w-4" />
          </button>
        </div>
        {advancedOpen ? (
          <div className="grid gap-5 border-t border-fog/60 bg-paper/70 px-6 py-6 md:grid-cols-3">
            <section className="rounded-2xl border border-fog/60 bg-white/80 p-4">
              <div className="section-label">Mode Focus</div>
              <p className="mt-2 text-sm leading-6 text-slate/70">
                Meridian will bias the query toward the selected track.
              </p>
              <div className="mt-4 rounded-xl border border-teal/15 bg-teal/10 px-3 py-2 text-sm font-semibold text-teal">
                {activeMode}
              </div>
            </section>

            <section className="rounded-2xl border border-fog/60 bg-white/80 p-4">
              <div className="section-label">Evidence Rules</div>
              <label className="mt-4 flex items-start gap-3 text-sm text-slate/75">
                <input
                  checked={options.recentOnly}
                  className="mt-1 h-4 w-4 rounded border-fog/80 text-teal focus:ring-teal"
                  onChange={(event) =>
                    onOptionsChange({ ...options, recentOnly: event.target.checked })
                  }
                  type="checkbox"
                />
                <span>Prefer the most recent available evidence.</span>
              </label>
              <label className="mt-3 flex items-start gap-3 text-sm text-slate/75">
                <input
                  checked={options.requireMultipleSources}
                  className="mt-1 h-4 w-4 rounded border-fog/80 text-teal focus:ring-teal"
                  onChange={(event) =>
                    onOptionsChange({
                      ...options,
                      requireMultipleSources: event.target.checked,
                    })
                  }
                  type="checkbox"
                />
                <span>Push Meridian to use multiple complementary sources.</span>
              </label>
            </section>

            <section className="rounded-2xl border border-fog/60 bg-white/80 p-4">
              <div className="section-label">Report Depth</div>
              <div className="mt-4 grid gap-2">
                {(['standard', 'deep'] as const).map((depth) => (
                  <button
                    key={depth}
                    className={`rounded-xl border px-3 py-2 text-left text-sm transition ${
                      options.reportDepth === depth
                        ? 'border-teal/30 bg-teal/10 text-teal'
                        : 'border-fog/70 bg-white text-slate/75 hover:border-teal/20'
                    }`}
                    onClick={() => onOptionsChange({ ...options, reportDepth: depth })}
                    type="button"
                  >
                    {depth === 'deep' ? 'Deep-dive synthesis' : 'Standard report'}
                  </button>
                ))}
              </div>
            </section>
          </div>
        ) : null}
      </div>
    </section>
  );
}
