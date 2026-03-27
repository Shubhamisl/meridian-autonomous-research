export interface ResearchJobSummary {
  id: string;
  status: string;
  query?: string;
}

export interface ResearchReport {
  id: string;
  job_id: string;
  query: string;
  markdown_content: string;
}

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

export async function createResearchJob(getToken: () => Promise<string | null>, query: string) {
  const response = await authFetch(getToken, '/api/research/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query }),
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
  return (await response.json()) as ResearchReport;
}
