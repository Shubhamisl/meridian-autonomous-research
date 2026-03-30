import { fireEvent, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import ResearchDashboardPage from '../ResearchDashboardPage';
import { renderWithProviders } from '../../test/render-with-providers';
import { createResearchJob, fetchResearchJobs } from '../../lib/api';
import { useLocation, useNavigate } from 'react-router-dom';

const navigateMock = vi.fn();
const getTokenMock = vi.fn(async () => 'token-123');
const locationMock = vi.fn();

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
    useLocation: vi.fn(),
    useNavigate: vi.fn(),
  };
});

const mockedFetchResearchJobs = vi.mocked(fetchResearchJobs);
const mockedCreateResearchJob = vi.mocked(createResearchJob);
const mockedUseLocation = vi.mocked(useLocation);
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
    locationMock.mockReset();
    locationMock.mockReturnValue({
      pathname: '/dashboard',
      search: '',
      hash: '',
      key: 'dashboard',
      state: null,
    });
    mockedUseLocation.mockImplementation(locationMock);
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
        state: {
          query: 'How should Meridian track this market?',
          activeMode: 'General',
        },
      });
    });
    expect(mockedCreateResearchJob).toHaveBeenCalledWith(
      getTokenMock,
      'How should Meridian track this market?',
      'How should Meridian track this market? Prioritize recent developments and recent evidence where possible.',
      {
        recentOnly: true,
        requireMultipleSources: true,
        reportDepth: 'standard',
      },
    );
  });

  it('resets mode to General when starting a new research from the dashboard', async () => {
    mockedFetchResearchJobs.mockResolvedValue([]);

    renderWithProviders(<ResearchDashboardPage />);

    fireEvent.click(screen.getByRole('button', { name: /^intelligence$/i }));
    fireEvent.click(screen.getByRole('button', { name: /new research/i }));

    expect(navigateMock).toHaveBeenLastCalledWith('/dashboard', {
      state: { prefillQuery: '', prefillMode: 'General', resetComposer: true },
    });
  });

  it('resets hidden advanced parameters on the explicit New Research flow', async () => {
    mockedFetchResearchJobs.mockResolvedValue([]);
    locationMock.mockReturnValue({
      pathname: '/dashboard',
      search: '',
      hash: '',
      key: 'dashboard',
      state: null,
    });

    const { rerender } = renderWithProviders(<ResearchDashboardPage />);

    fireEvent.click(await screen.findByRole('button', { name: /advanced parameters/i }));
    fireEvent.click(screen.getByRole('button', { name: /deep-dive synthesis/i }));
    fireEvent.click(screen.getByRole('checkbox', {
      name: /prefer the most recent available evidence/i,
    }));
    fireEvent.click(screen.getByRole('checkbox', {
      name: /push meridian to use multiple complementary sources/i,
    }));
    fireEvent.click(screen.getByRole('button', { name: /hide advanced parameters/i }));
    fireEvent.click(screen.getByRole('button', { name: /^intelligence$/i }));

    locationMock.mockReturnValue({
      pathname: '/dashboard',
      search: '',
      hash: '',
      key: 'dashboard-reset',
      state: { prefillQuery: '', prefillMode: 'General', resetComposer: true },
    });
    rerender(<ResearchDashboardPage />);

    expect(screen.getByPlaceholderText(/describe your research objective/i)).toHaveValue('');
    fireEvent.click(screen.getByRole('button', { name: /advanced parameters/i }));

    const recentOnlyCheckbox = screen.getByRole('checkbox', {
      name: /prefer the most recent available evidence/i,
    });
    const multipleSourcesCheckbox = screen.getByRole('checkbox', {
      name: /push meridian to use multiple complementary sources/i,
    });

    expect(screen.getByText('Mode Focus')).toBeInTheDocument();
    expect(screen.getAllByText('General').length).toBeGreaterThan(0);
    expect(recentOnlyCheckbox).toBeChecked();
    expect(multipleSourcesCheckbox).toBeChecked();
    expect(screen.getByRole('button', { name: /standard report/i })).toHaveClass('border-teal/30');
  });
});
