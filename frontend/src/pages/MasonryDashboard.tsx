import { useState, useEffect, useCallback } from 'react';
import Masonry from 'react-masonry-css';
import { AnimatePresence } from 'framer-motion';
import Navbar from '../components/Navbar';
import ResearchCard from '../components/ResearchCard';
import ReportViewer from '../components/ReportViewer';
import { useAuth } from '../contexts/AuthContext';

interface Job {
  id: string;
  status: string;
  query?: string;
}

interface ReportData {
  id: string;
  job_id: string;
  query: string;
  markdown_content: string;
}

export default function MasonryDashboard() {
  const { getToken } = useAuth();
  const [query, setQuery] = useState('');
  const [jobs, setJobs] = useState<Job[]>([]);
  const [reports, setReports] = useState<Record<string, ReportData>>({});
  const [selectedReport, setSelectedReport] = useState<ReportData | null>(null);
  const [loading, setLoading] = useState(false);

  const authFetch = useCallback(async (url: string, opts: RequestInit = {}) => {
    const token = await getToken();
    return fetch(url, {
      ...opts,
      headers: { ...opts.headers as Record<string, string>, Authorization: `Bearer ${token}` },
    });
  }, [getToken]);

  // Load all user jobs
  const loadJobs = useCallback(async () => {
    try {
      const res = await authFetch('/api/research/');
      if (res.ok) {
        const data = await res.json();
        setJobs(data);
      }
    } catch { /* ignore */ }
  }, [authFetch]);

  useEffect(() => {
    loadJobs();
    const interval = setInterval(loadJobs, 5000);
    return () => clearInterval(interval);
  }, [loadJobs]);

  // Fetch report for completed jobs
  useEffect(() => {
    jobs.forEach(async (job) => {
      if (job.status === 'completed' && !reports[job.id]) {
        try {
          const res = await authFetch(`/api/research/${job.id}/report`);
          if (res.ok) {
            const data = await res.json();
            setReports((prev) => ({ ...prev, [job.id]: data }));
          }
        } catch { /* ignore */ }
      }
    });
  }, [jobs, reports, authFetch]);

  const handleSubmit = async () => {
    if (!query.trim()) return;
    setLoading(true);
    try {
      const res = await authFetch('/api/research/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query }),
      });
      if (res.ok) {
        const data = await res.json();
        setJobs((prev) => [{ id: data.id, status: data.status, query }, ...prev]);
        setQuery('');
      }
    } finally {
      setLoading(false);
    }
  };

  const masonryBreakpoints = { default: 3, 1100: 2, 700: 1 };

  if (selectedReport) {
    return (
      <div className="min-h-screen bg-background">
        <nav className="sticky top-0 z-50 glass-card border-b border-white/5 px-6 py-3">
          <div className="max-w-7xl mx-auto flex items-center gap-4">
            <button
              onClick={() => setSelectedReport(null)}
              className="text-white/60 hover:text-white text-sm flex items-center gap-2 transition-colors"
            >
              ← Back to Dashboard
            </button>
          </div>
        </nav>
        <div className="max-w-4xl mx-auto px-6 py-8">
          <ReportViewer report={selectedReport} />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <Navbar query={query} onQueryChange={setQuery} onSubmit={handleSubmit} loading={loading} />

      <main className="max-w-7xl mx-auto px-6 py-8">
        {jobs.length === 0 ? (
          <div className="text-center mt-32">
            <h2 className="text-2xl font-bold text-white/80 mb-3">What shall we research?</h2>
            <p className="text-white/40 text-sm max-w-md mx-auto">
              Enter a topic in the search bar above and Meridian will autonomously orchestrate
              internet searches, academic papers, and synthesize a comprehensive report.
            </p>
          </div>
        ) : (
          <Masonry
            breakpointCols={masonryBreakpoints}
            className="masonry-grid"
            columnClassName="masonry-grid-column"
          >
            <AnimatePresence>
              {jobs.map((job) => (
                <ResearchCard
                  key={job.id}
                  id={job.id}
                  query={job.query || 'Research Job'}
                  status={job.status}
                  report={reports[job.id]?.markdown_content}
                  onClick={() => reports[job.id] && setSelectedReport(reports[job.id])}
                />
              ))}
            </AnimatePresence>
          </Masonry>
        )}
      </main>
    </div>
  );
}
