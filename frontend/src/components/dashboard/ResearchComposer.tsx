import { ArrowRight, SlidersHorizontal } from 'lucide-react';

interface ResearchComposerProps {
  query: string;
  loading: boolean;
  onQueryChange: (value: string) => void;
  onSubmit: () => void;
}

export default function ResearchComposer({
  query,
  loading,
  onQueryChange,
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
          <button className="inline-flex items-center gap-2 text-sm font-medium text-teal transition hover:text-ink">
            <SlidersHorizontal className="h-4 w-4" />
            <span>Advanced Parameters</span>
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
      </div>
    </section>
  );
}
