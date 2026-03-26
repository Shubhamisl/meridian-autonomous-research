import { useAuth } from '../contexts/AuthContext';
import { Search, LogOut } from 'lucide-react';

interface NavbarProps {
  query: string;
  onQueryChange: (q: string) => void;
  onSubmit: () => void;
  loading: boolean;
}

export default function Navbar({ query, onQueryChange, onSubmit, loading }: NavbarProps) {
  const { user, logout } = useAuth();

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && query.trim()) onSubmit();
  };

  return (
    <nav className="sticky top-0 z-50 glass-card border-b border-white/5 px-6 py-3">
      <div className="max-w-7xl mx-auto flex items-center gap-4">
        {/* Logo */}
        <div className="flex items-center gap-2.5 shrink-0">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white font-bold text-sm">
            M
          </div>
          <span className="text-lg font-bold text-white tracking-tight hidden sm:block">Meridian</span>
        </div>

        {/* Search */}
        <div className="flex-1 max-w-2xl mx-auto relative">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-white/30" />
          <input
            type="text"
            value={query}
            onChange={(e) => onQueryChange(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Research any topic..."
            className="w-full bg-white/5 border border-white/10 rounded-xl py-2.5 pl-10 pr-24 text-white placeholder-white/30 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500/50 transition-all"
          />
          <button
            onClick={onSubmit}
            disabled={!query.trim() || loading}
            className="absolute right-1.5 top-1/2 -translate-y-1/2 bg-gradient-to-r from-indigo-500 to-purple-600 text-white text-xs font-semibold px-4 py-1.5 rounded-lg disabled:opacity-40 hover:opacity-90 transition-opacity"
          >
            {loading ? 'Working...' : 'Research'}
          </button>
        </div>

        {/* User */}
        <div className="flex items-center gap-3 shrink-0">
          {user?.photoURL && (
            <img src={user.photoURL} alt="" className="w-8 h-8 rounded-full ring-2 ring-white/10" />
          )}
          <button
            onClick={logout}
            className="text-white/40 hover:text-white/80 transition-colors"
            title="Sign out"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </nav>
  );
}
