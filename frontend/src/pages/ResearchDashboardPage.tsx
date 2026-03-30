import { useCallback, useEffect, useMemo, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';

import RecentResearchList from '../components/dashboard/RecentResearchList';
import ResearchComposer, {
  type AdvancedResearchOptions,
} from '../components/dashboard/ResearchComposer';
import StarterModes from '../components/dashboard/StarterModes';
import AppShell from '../components/layout/AppShell';
import { useAuth } from '../contexts/useAuth';
import {
  createResearchJob,
  fetchResearchJobs,
  type ResearchJobSummary,
} from '../lib/api';
import { type ResearchMode } from '../lib/research-modes';

export default function ResearchDashboardPage() {
  const navigate = useNavigate();
  const { state } = useLocation() as { state: { prefillQuery?: string; prefillMode?: ResearchMode } | null };
  const { getToken } = useAuth();
  const [query, setQuery] = useState('');
  const [activeMode, setActiveMode] = useState<ResearchMode>('General');
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [advancedOptions, setAdvancedOptions] = useState<AdvancedResearchOptions>({
    recentOnly: true,
    requireMultipleSources: true,
    reportDepth: 'standard',
  });
  const [jobs, setJobs] = useState<ResearchJobSummary[]>([]);
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
    if (state?.prefillQuery !== undefined) {
      setQuery(state.prefillQuery);
    }
    if (state?.prefillMode) {
      setActiveMode(state.prefillMode);
    }
  }, [state?.prefillMode, state?.prefillQuery]);

  useEffect(() => {
    void loadJobs();
    const interval = window.setInterval(() => {
      void loadJobs();
    }, 5000);

    return () => window.clearInterval(interval);
  }, [loadJobs]);

  const displayJobs = useMemo(
    () =>
      jobs.map((job) => ({
        ...job,
        query: localQueries[job.id] ?? job.query,
      })),
    [jobs, localQueries],
  );

  const handleSubmit = useCallback(async () => {
    if (!query.trim()) return;

    setLoading(true);

    try {
      const queryParts = [query.trim()];
      if (activeMode !== 'General') {
        queryParts.push(`Treat this as a ${activeMode.toLowerCase()} research request.`);
      }
      if (advancedOptions.recentOnly) {
        queryParts.push('Prioritize recent developments and recent evidence where possible.');
      }
      if (advancedOptions.requireMultipleSources) {
        queryParts.push('Use multiple complementary sources rather than relying on a single source.');
      }
      if (advancedOptions.reportDepth === 'deep') {
        queryParts.push('Provide a deeper analysis with more supporting detail and tradeoffs.');
      }

      const finalQuery = queryParts.join(' ');
      const created = await createResearchJob(getToken, query, finalQuery);
      setLocalQueries((current) => ({ ...current, [created.id]: query }));
      setJobs((current) => [{ ...created, query }, ...current]);
      navigate(`/workspace/${created.id}`, { state: { query, activeMode } });
      setQuery('');
    } finally {
      setLoading(false);
    }
  }, [activeMode, advancedOptions, getToken, navigate, query]);

  const handleModeSelect = useCallback((mode: ResearchMode) => {
    setActiveMode(mode);
  }, []);

  return (
    <AppShell activeMode={activeMode} onSelectMode={handleModeSelect}>
      <ResearchComposer
        activeMode={activeMode}
        advancedOpen={advancedOpen}
        loading={loading}
        onOptionsChange={setAdvancedOptions}
        query={query}
        options={advancedOptions}
        onQueryChange={setQuery}
        onSubmit={handleSubmit}
        onToggleAdvanced={() => setAdvancedOpen((current) => !current)}
      />

      <StarterModes
        onSelectPrompt={(value) => {
          setQuery(value);
        }}
      />

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
