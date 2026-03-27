import { fireEvent, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import ResearchDashboardPage from '../ResearchDashboardPage';
import { renderWithProviders } from '../../test/render-with-providers';
import { createResearchJob, fetchResearchJobs } from '../../lib/api';
import { useNavigate } from 'react-router-dom';

const navigateMock = vi.fn();
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
    createResearchJob: vi.fn(),
    fetchResearchJobs: vi.fn(),
  };
});

vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>();

  return {
    ...actual,
    useNavigate: vi.fn(),
  };
});

const mockedFetchResearchJobs = vi.mocked(fetchResearchJobs);
const mockedCreateResearchJob = vi.mocked(createResearchJob);
const mockedUseNavigate = vi.mocked(useNavigate);

describe('ResearchDashboardPage', () => {
  beforeEach(() => {
    authState = {
      ...authState,
      getToken: getTokenMock,
    };
    mockedFetchResearchJobs.mockReset();
    mockedCreateResearchJob.mockReset();
    navigateMock.mockReset();
    mockedUseNavigate.mockReturnValue(navigateMock);
    getTokenMock.mockResolvedValue('token-123');
  });

  it('renders recent jobs from the API and preserves the listed query values', async () => {
    mockedFetchResearchJobs.mockResolvedValue([
      {
        id: 'job-pending',
        status: 'running',
        query: 'Pending query from API',
      },
      {
        id: 'job-completed',
        status: 'completed',
        query: 'Summary query from API',
      },
    ]);

    renderWithProviders(<ResearchDashboardPage />);

    expect(await screen.findByText('Pending query from API')).toBeInTheDocument();
    expect(await screen.findByText('Summary query from API')).toBeInTheDocument();
  });

  it('navigates to the workspace when job creation succeeds', async () => {
    mockedFetchResearchJobs.mockResolvedValue([]);
    mockedCreateResearchJob.mockResolvedValue({
      id: 'job-789',
      status: 'queued',
      query: 'How should Meridian track this market?',
    });

    renderWithProviders(<ResearchDashboardPage />);

    fireEvent.change(screen.getByPlaceholderText(/describe your research objective/i), {
      target: { value: 'How should Meridian track this market?' },
    });
    fireEvent.click(screen.getByRole('button', { name: /start research/i }));

    await waitFor(() => {
      expect(navigateMock).toHaveBeenCalledWith('/workspace/job-789', {
        state: { query: 'How should Meridian track this market?' },
      });
    });
    expect(mockedCreateResearchJob).toHaveBeenCalledWith(
      getTokenMock,
      'How should Meridian track this market?',
    );
  });
});
