import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import RecentResearchList from '../components/dashboard/RecentResearchList';
import ResearchComposer from '../components/dashboard/ResearchComposer';
import StarterModes from '../components/dashboard/StarterModes';
import AppShell from '../components/layout/AppShell';
import { useAuth } from '../contexts/useAuth';
import {
  createResearchJob,
  fetchResearchJobs,
  fetchResearchReport,
  type ResearchJobSummary,
  type ResearchReport,
} from '../lib/api';

export default function ResearchDashboardPage() {
  const navigate = useNavigate();
  const { getToken } = useAuth();
  const [query, setQuery] = useState('');
  const [jobs, setJobs] = useState<ResearchJobSummary[]>([]);
  const [reports, setReports] = useState<Record<string, ResearchReport>>({});
  const [localQueries, setLocalQueries] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);

  const loadJobs = useCallback(async () => {
    try {
      const nextJobs = await fetchResearchJobs(getToken);
      setJobs(nextJobs);
    } catch {
      // Keep the dashboard calm if polling fails; the workspace still handles direct job routes.
    }
  }, [getToken]);

  useEffect(() => {
    void loadJobs();
    const interval = window.setInterval(() => {
      void loadJobs();
    }, 5000);

    return () => window.clearInterval(interval);
  }, [loadJobs]);

  useEffect(() => {
    jobs.forEach((job) => {
      if (job.status !== 'completed' || reports[job.id]) return;

      void fetchResearchReport(getToken, job.id)
        .then((report) => {
          setReports((current) => ({ ...current, [job.id]: report }));
        })
        .catch(() => {
          // Older or unavailable jobs can remain without report preview data.
        });
    });
  }, [getToken, jobs, reports]);

  const displayJobs = useMemo(
    () =>
      jobs.map((job) => ({
        ...job,
        query: reports[job.id]?.query ?? localQueries[job.id] ?? job.query,
      })),
    [jobs, localQueries, reports],
  );

  const handleSubmit = useCallback(async () => {
    if (!query.trim()) return;

    setLoading(true);

    try {
      const created = await createResearchJob(getToken, query);
      setLocalQueries((current) => ({ ...current, [created.id]: query }));
      setJobs((current) => [{ ...created, query }, ...current]);
      navigate(`/workspace/${created.id}`, { state: { query } });
      setQuery('');
    } finally {
      setLoading(false);
    }
  }, [getToken, navigate, query]);

  return (
    <AppShell>
      <ResearchComposer
        loading={loading}
        query={query}
        onQueryChange={setQuery}
        onSubmit={handleSubmit}
      />

      <StarterModes onSelectPrompt={setQuery} />

      <section className="mb-16 rounded-[1.75rem] bg-slate px-8 py-7 text-white shadow-panel">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <div className="section-label !text-teal-soft">Trusted Processing Pipeline</div>
            <h2 className="mt-3 font-serif text-3xl font-semibold tracking-tight">
              Meridian translates complex research into readable intelligence.
            </h2>
          </div>
          <div className="grid gap-3 text-sm text-white/80 md:grid-cols-2 xl:grid-cols-4">
            <div>Meridian classifies the domain</div>
            <div>Routes the best sources</div>
            <div>Scores evidence credibility</div>
            <div>Builds the final report</div>
          </div>
        </div>
      </section>

      <RecentResearchList jobs={displayJobs} onOpenJob={(jobId) => navigate(`/workspace/${jobId}`)} />
    </AppShell>
  );
}
