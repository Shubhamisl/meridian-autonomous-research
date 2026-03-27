import { ArrowUpRight } from 'lucide-react';

import type { ResearchWorkspaceEvidenceItem } from '../../lib/api';

interface EvidencePlaceholderProps {
  evidence: ResearchWorkspaceEvidenceItem[];
}

function formatCredibilityScore(score: number) {
  return score.toFixed(2);
}

function formatSourceLabel(source: string) {
  return source.replace(/_/g, ' ');
}

export default function EvidencePlaceholder({ evidence }: EvidencePlaceholderProps) {
  return (
    <section className="rounded-[1.75rem] border border-fog/60 bg-white/88 p-8 shadow-soft">
      <div className="section-label">Evidence Surface</div>
      <div className="mt-3 flex flex-wrap items-end justify-between gap-4">
        <h2 className="font-serif text-3xl font-semibold tracking-tight text-ink">
          Evidence returned by the API
        </h2>
        <p className="max-w-2xl text-sm leading-7 text-slate/72">
          Meridian only renders source cards that the workspace payload actually returns.
        </p>
      </div>

      {evidence.length > 0 ? (
        <div className="mt-8 space-y-4">
          {evidence.map((item, index) => (
            <article
              key={`${item.source}-${item.title}-${index}`}
              className="rounded-2xl border border-fog/60 bg-paper/75 p-5"
            >
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div className="space-y-3">
                  <div className="flex flex-wrap items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-slate/55">
                    <span className="rounded-full bg-teal/10 px-3 py-1 text-teal">
                      {formatSourceLabel(item.source)}
                    </span>
                    <span>Evidence {String(index + 1).padStart(2, '0')}</span>
                  </div>
                  <h3 className="font-serif text-xl font-semibold leading-tight tracking-tight text-ink">
                    {item.title}
                  </h3>
                </div>
                <div className="rounded-full border border-teal/15 bg-teal/10 px-3 py-1 text-sm font-medium text-teal">
                  Credibility {formatCredibilityScore(item.credibility_score)}
                </div>
              </div>

              {item.snippet ? (
                <p className="mt-4 text-sm leading-7 text-slate/72">{item.snippet}</p>
              ) : (
                <p className="mt-4 text-sm leading-7 text-slate/55">
                  No snippet was returned for this evidence item.
                </p>
              )}

              {item.url ? (
                <a
                  className="mt-4 inline-flex items-center gap-1 text-sm font-semibold text-teal transition hover:text-ink"
                  href={item.url}
                  rel="noreferrer"
                  target="_blank"
                >
                  Original source
                  <ArrowUpRight className="h-4 w-4" />
                </a>
              ) : null}
            </article>
          ))}
        </div>
      ) : (
        <div className="mt-8 rounded-2xl border border-dashed border-fog/70 bg-white/75 p-6">
          <h3 className="text-base font-semibold text-ink">No evidence items were returned</h3>
          <p className="mt-2 text-sm leading-7 text-slate/68">
            The current workspace payload does not include source cards yet, so Meridian keeps this
            section empty rather than inventing unsupported evidence.
          </p>
        </div>
      )}
    </section>
  );
}
