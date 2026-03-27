import { motion } from 'framer-motion';
import { Navigate } from 'react-router-dom';

import { useAuth } from '../contexts/useAuth';

export default function LoginPage() {
  const { user, login, isConfigured, setupMessage } = useAuth();

  if (user) return <Navigate to="/dashboard" replace />;

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-ivory px-6 py-16">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(15,118,110,0.10),transparent_24%),radial-gradient(circle_at_bottom_right,rgba(37,99,235,0.07),transparent_22%)]" />
      <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-fog to-transparent" />

      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: 'easeOut' }}
        className="editorial-panel relative z-10 mx-4 w-full max-w-lg overflow-hidden p-10 text-center"
      >
        <div className="absolute inset-x-10 top-0 h-px bg-gradient-to-r from-transparent via-teal/50 to-transparent" />

        <div className="mb-10">
          <div className="mb-8 inline-flex items-center gap-4">
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-teal/20 bg-teal text-sm font-bold text-white shadow-soft">
              M
            </div>
            <div className="text-left">
              <div className="font-serif text-3xl font-bold tracking-tight text-ink">Meridian</div>
              <div className="section-label mt-1 text-[10px]">Autonomous Research Intelligence</div>
            </div>
          </div>

          <h1 className="font-serif text-4xl font-semibold tracking-tight text-ink">
            {isConfigured ? 'Enter the research workspace' : 'Finish workspace setup'}
          </h1>
          <p className="mx-auto mt-4 max-w-md text-sm leading-7 text-slate/75">
            {isConfigured
              ? "Sign in to access Meridian's guided dashboard, revisit prior syntheses, and open full report workspaces with evidence-aware intelligence."
              : 'Meridian can render the new workspace shell, but Google sign-in is paused until the frontend Firebase environment variables are added.'}
          </p>
        </div>

        <button
          onClick={login}
          disabled={!isConfigured}
          className={`group flex w-full items-center justify-center gap-3 rounded-2xl border px-6 py-4 font-semibold shadow-soft transition-all duration-200 active:translate-y-0 ${
            isConfigured
              ? 'border-ink/10 bg-white text-ink hover:-translate-y-0.5 hover:border-teal/20 hover:shadow-panel'
              : 'cursor-not-allowed border-fog/80 bg-paper text-slate/45'
          }`}
        >
          <svg className="h-5 w-5" viewBox="0 0 24 24">
            <path
              fill="#4285F4"
              d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"
            />
            <path
              fill="#34A853"
              d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
            />
            <path
              fill="#FBBC05"
              d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
            />
            <path
              fill="#EA4335"
              d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
            />
          </svg>
          <span>{isConfigured ? 'Continue with Google' : 'Google sign-in needs setup'}</span>
        </button>

        {isConfigured ? (
          <div className="mt-8 rounded-2xl border border-fog/70 bg-paper px-5 py-4 text-left">
            <div className="section-label text-[10px]">What happens after sign-in</div>
            <p className="mt-2 text-sm leading-6 text-slate/75">
              Start a new inquiry from the dashboard, revisit previous runs, and open report
              workspaces that keep the answer first while making evidence and reasoning inspectable.
            </p>
          </div>
        ) : (
          <div className="mt-8 rounded-2xl border border-amber/25 bg-amber/10 px-5 py-4 text-left">
            <div className="section-label !text-amber text-[10px]">Setup required</div>
            <p className="mt-2 text-sm leading-6 text-slate/80">
              {setupMessage ?? 'Firebase sign-in is not configured yet.'}
            </p>
            <p className="mt-3 text-xs leading-6 text-slate/60">
              Copy `frontend/.env.example` to `frontend/.env` and supply the real Firebase values
              to unlock dashboard and workspace access.
            </p>
          </div>
        )}

        <p className="mt-8 text-xs tracking-wide text-slate/45">
          Meridian Research Workspace (c) 2026
        </p>
      </motion.div>
    </div>
  );
}
