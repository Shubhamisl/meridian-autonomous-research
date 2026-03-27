import { fireEvent, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import LoginPage from '../LoginPage';
import { renderWithProviders } from '../../test/render-with-providers';

const loginMock = vi.fn(async () => undefined);

let authState: {
  user: null;
  login: typeof loginMock;
  isConfigured: boolean;
  setupMessage: string | null;
  logout: ReturnType<typeof vi.fn>;
  getToken: ReturnType<typeof vi.fn>;
} = {
  user: null,
  login: loginMock,
  isConfigured: false,
  setupMessage: 'Add the Firebase frontend environment values before signing in.',
  logout: vi.fn(async () => undefined),
  getToken: vi.fn(async () => null),
};

vi.mock('../../contexts/useAuth', () => ({
  useAuth: () => authState,
}));

describe('LoginPage', () => {
  beforeEach(() => {
    authState = {
      user: null,
      login: vi.fn(async () => undefined),
      isConfigured: false,
      setupMessage: 'Add the Firebase frontend environment values before signing in.',
      logout: vi.fn(async () => undefined),
      getToken: vi.fn(async () => null),
    };
  });

  it('renders setup guidance when Firebase is not configured', () => {
    renderWithProviders(<LoginPage />);

    expect(screen.getByRole('heading', { name: /finish workspace setup/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /google sign-in needs setup/i })).toBeDisabled();
    expect(screen.getByText('Add the Firebase frontend environment values before signing in.')).toBeInTheDocument();
    expect(screen.getByText(/frontend\/\.env\.example/i)).toBeInTheDocument();
  });

  it('renders the sign-in flow when Firebase is configured', () => {
    const login = vi.fn(async () => undefined);
    authState = {
      ...authState,
      login,
      isConfigured: true,
      setupMessage: null,
    };

    renderWithProviders(<LoginPage />);

    expect(screen.getByRole('heading', { name: /enter the research workspace/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /continue with google/i })).toBeEnabled();
    expect(screen.getByText(/what happens after sign-in/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /continue with google/i }));

    expect(login).toHaveBeenCalledTimes(1);
  });
});
