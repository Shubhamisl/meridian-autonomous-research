export interface ResearchJobSummary {
  id: string;
  status: string;
  query?: string;
}

export interface ResearchWorkspacePipeline {
  current_phase: string | null;
  phases: string[];
}

export interface ResearchWorkspaceEvidenceItem {
  source: string;
  title: string;
  credibility_score: number;
  snippet: string | null;
  url: string | null;
}

export interface ResearchWorkspaceQueryRefinement {
  source: string;
  raw_query: string;
  enriched_query: string;
}

export interface ResearchWorkspaceExplainability {
  active_sources: string[];
  query_refinements: ResearchWorkspaceQueryRefinement[];
}

export interface ResearchWorkspacePayload {
  id: string;
  job_id: string;
  query: string;
  markdown_content: string;
  domain: string | null;
  format_label: string | null;
  pipeline: ResearchWorkspacePipeline;
  evidence: ResearchWorkspaceEvidenceItem[];
  explainability: ResearchWorkspaceExplainability;
}

export type ResearchReport = ResearchWorkspacePayload;

export async function authFetch(
  getToken: () => Promise<string | null>,
  url: string,
  opts: RequestInit = {},
) {
  const token = await getToken();
  const headers = {
    ...(opts.headers as Record<string, string> | undefined),
  };

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  return fetch(url, {
    ...opts,
    headers,
  });
}

export async function fetchResearchJobs(getToken: () => Promise<string | null>) {
  const response = await authFetch(getToken, '/api/research/');
  if (!response.ok) throw new Error('Failed to load research jobs');
  return (await response.json()) as ResearchJobSummary[];
}

export async function createResearchJob(
  getToken: () => Promise<string | null>,
  query: string,
  executionQuery = query,
) {
  const response = await authFetch(getToken, '/api/research/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, execution_query: executionQuery }),
  });

  if (!response.ok) throw new Error('Failed to start research');
  return (await response.json()) as ResearchJobSummary;
}

export async function fetchResearchStatus(getToken: () => Promise<string | null>, jobId: string) {
  const response = await authFetch(getToken, `/api/research/${jobId}`);
  if (!response.ok) throw new Error('Failed to load research status');
  return (await response.json()) as ResearchJobSummary;
}

export async function fetchResearchReport(getToken: () => Promise<string | null>, jobId: string) {
  const response = await authFetch(getToken, `/api/research/${jobId}/report`);
  if (!response.ok) throw new Error('Failed to load research report');
  return (await response.json()) as ResearchWorkspacePayload;
}
