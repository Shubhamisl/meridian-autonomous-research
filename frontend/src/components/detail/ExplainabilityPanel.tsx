import { getStatusMeta } from '../../lib/research-status';
import type { ResearchWorkspaceQueryRefinement } from '../../lib/api';

interface ExplainabilityPanelProps {
  status: string;
  activeSources: string[];
  queryRefinements: ResearchWorkspaceQueryRefinement[];
}

function formatSourceLabel(source: string) {
  return source.replace(/_/g, ' ');
}

function renderEmptyState(message: string) {
  return (
    <p className="mt-3 text-sm leading-7 text-slate/68">
      {message}
    </p>
  );
}

export default function ExplainabilityPanel({
  status,
  activeSources,
  queryRefinements,
}: ExplainabilityPanelProps) {
  const statusMeta = getStatusMeta(status);

  return (
    <aside className="editorial-panel p-6">
      <div className="section-label">Explain This Report</div>
      <p className="mt-3 text-sm leading-7 text-slate/72">{statusMeta.emphasis}</p>

      <div className="mt-6 space-y-5">
        <section className="rounded-2xl border border-fog/60 bg-white/80 p-4">
          <h3 className="text-sm font-semibold text-ink">Active Sources</h3>
          {activeSources.length > 0 ? (
            <div className="mt-3 flex flex-wrap gap-2">
              {activeSources.map((source) => (
                <span
                  key={source}
                  className="rounded-full border border-teal/15 bg-teal/10 px-3 py-1 text-sm font-medium text-teal"
                >
                  {formatSourceLabel(source)}
                </span>
              ))}
            </div>
          ) : (
            renderEmptyState('The API has not returned any active sources for this workspace yet.')
          )}
        </section>

        <section className="rounded-2xl border border-fog/60 bg-white/80 p-4">
          <h3 className="text-sm font-semibold text-ink">Query Refinements</h3>
          {queryRefinements.length > 0 ? (
            <div className="mt-3 space-y-3">
              {queryRefinements.map((refinement) => (
                <article
                  key={`${refinement.source}-${refinement.raw_query}`}
                  className="rounded-2xl border border-fog/60 bg-paper/70 p-4"
                >
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <span className="rounded-full border border-teal/15 bg-teal/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] text-teal">
                      {formatSourceLabel(refinement.source)}
                    </span>
                  </div>
                  <dl className="mt-4 space-y-3">
                    <div>
                      <dt className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate/55">
                        Raw query
                      </dt>
                      <dd className="mt-1 text-sm leading-6 text-ink">{refinement.raw_query}</dd>
                    </div>
                    <div>
                      <dt className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate/55">
                        Enriched query
                      </dt>
                      <dd className="mt-1 text-sm leading-6 text-slate/72">
                        {refinement.enriched_query}
                      </dd>
                    </div>
                  </dl>
                </article>
              ))}
            </div>
          ) : (
            renderEmptyState(
              'The API has not returned any query refinements for this workspace yet.',
            )
          )}
        </section>
      </div>
    </aside>
  );
}
