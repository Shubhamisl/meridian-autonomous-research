import { useCallback, useEffect, useState } from 'react';
import { useLocation, useParams } from 'react-router-dom';

import EvidencePlaceholder from '../components/detail/EvidencePlaceholder';
import ExplainabilityPanel from '../components/detail/ExplainabilityPanel';
import PipelineTimeline from '../components/detail/PipelineTimeline';
import ReportHeader from '../components/detail/ReportHeader';
import AppShell from '../components/layout/AppShell';
import ReportViewer from '../components/ReportViewer';
import { useAuth } from '../contexts/useAuth';
import { fetchResearchReport, fetchResearchStatus, type ResearchReport } from '../lib/api';

interface WorkspaceState {
  query?: string;
}

export default function ResearchWorkspacePage() {
  const { jobId = '' } = useParams();
  const { state } = useLocation() as { state: WorkspaceState | null };
  const initialQuery = state?.query ?? null;
  const { getToken } = useAuth();
  const [jobQuery, setJobQuery] = useState<string | null>(initialQuery);
  const [status, setStatus] = useState('pending');
  const [report, setReport] = useState<ResearchReport | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  const query = report?.query ?? jobQuery ?? 'Research inquiry';

  const loadWorkspace = useCallback(async () => {
    try {
      const nextStatus = await fetchResearchStatus(getToken, jobId);
      setStatus(nextStatus.status);
      setJobQuery(nextStatus.query ?? initialQuery);

      if (nextStatus.status === 'completed') {
        const nextReport = await fetchResearchReport(getToken, jobId);
        setReport(nextReport);
      }

      if (nextStatus.status === 'failed') {
        setLoadError('The report could not be completed. Meridian stopped before synthesis finished.');
      } else {
        setLoadError(null);
      }
    } catch {
      setLoadError('This workspace could not be loaded right now.');
    }
  }, [getToken, initialQuery, jobId]);

  useEffect(() => {
    const initialLoad = window.setTimeout(() => {
      void loadWorkspace();
    }, 0);

    const interval = window.setInterval(() => {
      void loadWorkspace();
    }, 5000);

    return () => {
      window.clearTimeout(initialLoad);
      window.clearInterval(interval);
    };
  }, [loadWorkspace]);

  return (
    <AppShell>
      <ReportHeader jobId={jobId} query={query} status={status} />
      <PipelineTimeline status={status} />

      <div className="grid gap-8 xl:grid-cols-[minmax(0,1fr)_340px]">
        <div className="space-y-8">
          {report ? (
            <ReportViewer report={report} />
          ) : (
            <section className="rounded-[1.75rem] border border-fog/60 bg-paper p-10 shadow-soft">
              <div className="section-label">Executive Summary</div>
              <div className="mt-4 space-y-4">
                <div className="h-8 w-3/4 rounded-full bg-white/80" />
                <div className="h-5 w-full rounded-full bg-white/80" />
                <div className="h-5 w-5/6 rounded-full bg-white/80" />
                <div className="h-5 w-4/6 rounded-full bg-white/80" />
              </div>
              <p className="mt-8 text-sm leading-7 text-slate/72">
                Meridian is still building this report. The workspace keeps the reading surface in
                place so progress feels continuous rather than hidden behind a spinner.
              </p>
            </section>
          )}

          {loadError ? (
            <section className="rounded-[1.75rem] border border-rose/20 bg-rose/5 p-8 text-rose shadow-soft">
              <div className="section-label !text-rose">Workspace Status</div>
              <p className="mt-3 text-sm leading-7">{loadError}</p>
            </section>
          ) : (
            <EvidencePlaceholder />
          )}
        </div>

        <ExplainabilityPanel status={status} />
      </div>
    </AppShell>
  );
}
