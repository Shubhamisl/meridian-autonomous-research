import { ArrowUpRight } from 'lucide-react';

import type { ResearchJobSummary } from '../../lib/api';
import { getStatusMeta } from '../../lib/research-status';

interface RecentResearchListProps {
  jobs: ResearchJobSummary[];
  onOpenJob: (jobId: string) => void;
}

export default function RecentResearchList({ jobs, onOpenJob }: RecentResearchListProps) {
  return (
    <section className="mb-8">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <div className="section-label">Recent Inquiries</div>
          <h2 className="mt-2 font-serif text-3xl font-semibold tracking-tight text-ink">
            Continue where Meridian left off
          </h2>
        </div>
      </div>

      <div className="space-y-4">
        {jobs.map((job) => {
          const statusMeta = getStatusMeta(job.status);

          return (
            <button
              key={job.id}
              className="flex w-full flex-col gap-4 rounded-2xl border border-fog/60 bg-white/88 p-6 text-left shadow-soft transition hover:border-teal/25 hover:shadow-panel md:flex-row md:items-center md:justify-between"
              onClick={() => onOpenJob(job.id)}
            >
              <div className="min-w-0">
                <h3 className="truncate font-medium text-ink">
                  {job.query ?? 'Research inquiry in progress'}
                </h3>
                <div className="mt-2 flex flex-wrap items-center gap-3 text-xs uppercase tracking-[0.16em] text-slate/55">
                  <span>{job.id.slice(0, 8)}</span>
                  <span className="h-1 w-1 rounded-full bg-fog" />
                  <span>Autonomous research job</span>
                </div>
              </div>
              <div className="flex items-center gap-4">
                <span className={`status-pill ${statusMeta.pillClassName}`}>{statusMeta.label}</span>
                <ArrowUpRight className="h-4 w-4 text-slate/55" />
              </div>
            </button>
          );
        })}
      </div>
    </section>
  );
}
