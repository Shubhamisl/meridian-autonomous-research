export default function EvidencePlaceholder() {
  return (
    <section className="rounded-[1.75rem] border border-fog/60 bg-white/88 p-8 shadow-soft">
      <div className="section-label">Evidence Surface</div>
      <h2 className="mt-3 font-serif text-3xl font-semibold tracking-tight text-ink">
        Source cards will appear here as the API grows
      </h2>
      <p className="mt-4 max-w-3xl text-sm leading-7 text-slate/72">
        Meridian already performs source routing, credibility scoring, and weighted retrieval in
        the backend. The current API returns the finished markdown report but not the per-source
        evidence payload yet, so this workspace preserves the section honestly instead of inventing
        unsupported details.
      </p>
    </section>
  );
}
