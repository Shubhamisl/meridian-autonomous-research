import type { ReactNode } from 'react';
import { Clock3, LogOut, Search, Sparkles, SquarePen } from 'lucide-react';
import { Link, useLocation, useNavigate } from 'react-router-dom';

import { useAuth } from '../../contexts/useAuth';
import { MODE_PROMPTS, RESEARCH_MODES, type ResearchMode } from '../../lib/research-modes';

interface AppShellProps {
  children: ReactNode;
  activeMode?: ResearchMode | null;
  onSelectMode?: (mode: ResearchMode) => void;
}

export default function AppShell({ children, activeMode = null, onSelectMode }: AppShellProps) {
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const inWorkspace = pathname.startsWith('/workspace/');

  const handleModeSelect = (mode: ResearchMode) => {
    if (onSelectMode) {
      onSelectMode(mode);
      if (pathname !== '/dashboard') {
        navigate('/dashboard', { state: { prefillQuery: MODE_PROMPTS[mode], prefillMode: mode } });
      }
      return;
    }

    navigate('/dashboard', { state: { prefillQuery: MODE_PROMPTS[mode], prefillMode: mode } });
  };

  return (
    <div className="min-h-screen bg-ivory text-ink">
      <aside className="fixed inset-y-0 left-0 hidden w-64 flex-col border-r border-fog/60 bg-white/75 px-6 py-8 backdrop-blur-sm lg:flex">
        <div className="mb-10 px-2">
          <div className="font-serif text-2xl font-bold tracking-tight text-ink">Meridian</div>
          <p className="mt-1 text-[10px] uppercase tracking-[0.22em] text-slate/60">
            Autonomous Research
          </p>
        </div>

        <button
          className="mb-8 inline-flex items-center justify-center gap-2 rounded-2xl bg-teal px-4 py-3 text-sm font-semibold text-white shadow-soft transition hover:bg-teal/90"
          onClick={() =>
            navigate('/dashboard', {
              state: { prefillQuery: '', prefillMode: 'General', resetComposer: true },
            })
          }
          type="button"
        >
          <SquarePen className="h-4 w-4" />
          <span>New Research</span>
        </button>

        <nav className="flex-1 space-y-1">
          {RESEARCH_MODES.map((mode) => (
            <button
              key={mode}
              type="button"
              className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition ${
                mode === activeMode
                  ? 'bg-teal-soft text-teal'
                  : 'text-slate/75 hover:bg-white hover:text-ink'
              }`}
              onClick={() => handleModeSelect(mode)}
            >
              <Sparkles className="h-4 w-4" />
              <span className="font-medium">{mode}</span>
            </button>
          ))}
        </nav>

        <div className="mt-8 space-y-2 border-t border-fog/60 pt-6 text-sm text-slate/70">
          <div className="rounded-xl px-3 py-2 hover:bg-white">Settings</div>
          <div className="rounded-xl px-3 py-2 hover:bg-white">Support</div>
        </div>
      </aside>

      <div className="lg:pl-64">
        <header className="sticky top-0 z-40 border-b border-fog/50 bg-white/82 backdrop-blur-md">
          <div className="mx-auto flex max-w-[1440px] items-center justify-between gap-6 px-6 py-4 lg:px-8">
            <div className="flex items-center gap-8">
              <Link className="font-serif text-2xl font-bold tracking-tight text-ink lg:hidden" to="/dashboard">
                Meridian
              </Link>
              <nav className="hidden items-center gap-7 md:flex">
                <Link
                  className={`border-b pb-1 text-sm font-medium transition ${
                    pathname === '/dashboard' ? 'border-teal text-ink' : 'border-transparent text-slate/65 hover:text-ink'
                  }`}
                  to="/dashboard"
                >
                  Dashboard
                </Link>
                {inWorkspace && <span className="text-sm font-medium text-slate/55">Workspace</span>}
              </nav>
            </div>

            <div className="flex items-center gap-3">
              <div className="hidden items-center gap-2 rounded-full border border-fog/70 bg-white px-4 py-2 text-sm text-slate/55 md:flex">
                <Search className="h-4 w-4" />
                <span>Search knowledge...</span>
              </div>
              <button
                className="rounded-full border border-fog/70 bg-white p-2 text-slate/65 transition hover:text-ink"
                onClick={() => navigate('/dashboard')}
                title="Open recent research"
                type="button"
              >
                <Clock3 className="h-4 w-4" />
              </button>
              <div className="hidden items-center gap-3 rounded-full border border-fog/70 bg-white px-3 py-2 md:flex">
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-teal text-xs font-bold text-white">
                  {user?.displayName?.[0] ?? 'M'}
                </div>
                <span className="max-w-[140px] truncate text-sm text-slate/75">
                  {user?.displayName ?? 'Researcher'}
                </span>
              </div>
              <button
                className="rounded-full border border-fog/70 bg-white p-2 text-slate/65 transition hover:text-ink"
                onClick={logout}
                title="Sign out"
              >
                <LogOut className="h-4 w-4" />
              </button>
            </div>
          </div>
        </header>

        <main className="mx-auto max-w-[1440px] px-6 py-10 lg:px-8">{children}</main>
      </div>
    </div>
  );
}
