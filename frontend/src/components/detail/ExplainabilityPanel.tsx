interface ExplainabilityPanelProps {
  status: string;
}

const sections = [
  {
    label: 'Domain Routing',
    text: 'The current API does not expose the classified domain or active source set yet, so this workspace reserves the space for that metadata once it is available.',
  },
  {
    label: 'Credibility Weighting',
    text: 'Meridian now scores evidence and weights retrieval quality in the backend. When chunk and evidence metadata are exposed, this panel can show those scores directly.',
  },
  {
    label: 'Query Refinement',
    text: 'Query enrichment runs before search dispatch, but the enriched queries are not yet returned by the API. This panel is intentionally honest about that gap.',
  },
];

export default function ExplainabilityPanel({ status }: ExplainabilityPanelProps) {
  return (
    <aside className="editorial-panel p-6">
      <div className="section-label">Explain This Report</div>
      <p className="mt-3 text-sm leading-7 text-slate/72">
        Meridian is currently {status}. The UI is ready for routing, credibility, and query
        details as soon as the API starts returning them.
      </p>

      <div className="mt-6 space-y-5">
        {sections.map((section) => (
          <section key={section.label} className="rounded-2xl border border-fog/60 bg-white/80 p-4">
            <h3 className="text-sm font-semibold text-ink">{section.label}</h3>
            <p className="mt-2 text-sm leading-6 text-slate/68">{section.text}</p>
          </section>
        ))}
      </div>
    </aside>
  );
}
