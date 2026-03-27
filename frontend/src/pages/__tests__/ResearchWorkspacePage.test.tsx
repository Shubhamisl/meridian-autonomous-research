import { screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import ResearchWorkspacePage from '../ResearchWorkspacePage';
import { renderWithProviders } from '../../test/render-with-providers';
import type { ResearchWorkspacePayload } from '../../lib/api';
import { fetchResearchReport, fetchResearchStatus } from '../../lib/api';

const getTokenMock = vi.fn(async () => 'token-123');

let authState = {
  user: { uid: 'user-1' },
  login: vi.fn(async () => undefined),
  isConfigured: true,
  setupMessage: null,
  logout: vi.fn(async () => undefined),
  getToken: getTokenMock,
};

vi.mock('../../contexts/useAuth', () => ({
  useAuth: () => authState,
}));

vi.mock('../../lib/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../lib/api')>();

  return {
    ...actual,
    fetchResearchStatus: vi.fn(),
    fetchResearchReport: vi.fn(),
  };
});

const mockedFetchResearchStatus = vi.mocked(fetchResearchStatus);
const mockedFetchResearchReport = vi.mocked(fetchResearchReport);

describe('ResearchWorkspacePage', () => {
  beforeEach(() => {
    authState = {
      ...authState,
      getToken: getTokenMock,
    };
    mockedFetchResearchStatus.mockReset();
    mockedFetchResearchReport.mockReset();
    getTokenMock.mockResolvedValue('token-123');
  });

  it('renders truthful workspace payload data from the API', async () => {
    const payload: ResearchWorkspacePayload = {
      id: 'workspace-123',
      job_id: 'job-123',
      query: 'How are battery supply chains changing?',
      markdown_content: '# Executive summary\nThe report is ready.',
      domain: 'supply_chain',
      format_label: 'briefing_note',
      pipeline: {
        current_phase: 'evidence_scoring',
        phases: ['ingestion', 'domain_classification', 'evidence_scoring', 'synthesis'],
      },
      evidence: [
        {
          source: 'news_wires',
          title: 'Battery plants expand in response to demand',
          credibility_score: 0.92,
          snippet: 'Reuters and regional reporting show factories scaling output.',
          url: 'https://example.com/battery',
        },
      ],
      explainability: {
        active_sources: ['news_wires', 'government_reports'],
        query_refinements: [
          {
            source: 'domain_classifier',
            raw_query: 'battery supply chains',
            enriched_query: 'battery supply chains, manufacturing capacity, and logistics constraints',
          },
        ],
      },
    };

    mockedFetchResearchStatus.mockResolvedValue({
      id: 'job-123',
      status: 'completed',
      query: 'How are battery supply chains changing?',
    });
    mockedFetchResearchReport.mockResolvedValue(payload);

    renderWithProviders(<ResearchWorkspacePage />, {
      route: '/workspace/job-123',
      path: '/workspace/:jobId',
    });

    expect(await screen.findByText('Domain: supply chain')).toBeInTheDocument();
    expect(screen.getByText('Format: briefing note')).toBeInTheDocument();
    expect(
      screen.getAllByRole('heading', { name: /how are battery supply chains changing\?/i }),
    ).toHaveLength(2);
    expect(screen.getByText('Battery plants expand in response to demand')).toBeInTheDocument();
    expect(screen.getByText('Reuters and regional reporting show factories scaling output.')).toBeInTheDocument();
    expect(screen.getByText('Current phase: Evidence Scoring')).toBeInTheDocument();
    expect(screen.getByText('battery supply chains')).toBeInTheDocument();
    expect(screen.getByText('battery supply chains, manufacturing capacity, and logistics constraints')).toBeInTheDocument();
    expect(screen.getAllByText('news wires')).toHaveLength(2);
    expect(screen.getByText('government reports')).toBeInTheDocument();
    expect(screen.getByText('Executive summary')).toBeInTheDocument();

    expect(mockedFetchResearchStatus).toHaveBeenCalledWith(getTokenMock, 'job-123');
    expect(mockedFetchResearchReport).toHaveBeenCalledWith(getTokenMock, 'job-123');
  });

  it('handles a failed workspace load with the reported status message', async () => {
    mockedFetchResearchStatus.mockResolvedValue({
      id: 'job-456',
      status: 'failed',
      query: 'Why did this inquiry fail?',
    });

    renderWithProviders(<ResearchWorkspacePage />, {
      route: '/workspace/job-456',
      path: '/workspace/:jobId',
    });

    expect(await screen.findByText(/the report could not be completed/i)).toBeInTheDocument();
    expect(screen.getByText(/meridian stopped before synthesis finished/i)).toBeInTheDocument();
    expect(mockedFetchResearchReport).not.toHaveBeenCalled();
  });
});
