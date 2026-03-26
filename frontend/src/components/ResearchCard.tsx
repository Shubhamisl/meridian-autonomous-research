import { motion } from 'framer-motion';
import { Clock, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';

interface ResearchCardProps {
  id: string;
  query: string;
  status: string;
  report?: string;
  onClick: () => void;
}

const statusConfig: Record<string, { icon: typeof Clock; color: string; label: string }> = {
  pending: { icon: Clock, color: 'text-yellow-400', label: 'Queued' },
  running: { icon: Loader2, color: 'text-blue-400', label: 'Researching' },
  completed: { icon: CheckCircle, color: 'text-emerald-400', label: 'Complete' },
  failed: { icon: AlertCircle, color: 'text-red-400', label: 'Failed' },
};

export default function ResearchCard({ id, query, status, report, onClick }: ResearchCardProps) {
  const cfg = statusConfig[status] || statusConfig.pending;
  const Icon = cfg.icon;
  const snippet = report ? report.replace(/[#*_[\]]/g, '').slice(0, 180) + '...' : null;

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      whileHover={{ scale: 1.02, y: -2 }}
      onClick={onClick}
      className="glass-card rounded-xl p-5 cursor-pointer border border-white/5 hover:border-indigo-500/30 transition-all duration-300 break-inside-avoid mb-4"
    >
      {/* Status badge */}
      <div className="flex items-center gap-2 mb-3">
        <Icon className={`w-3.5 h-3.5 ${cfg.color} ${status === 'running' ? 'animate-spin' : ''}`} />
        <span className={`text-xs font-medium ${cfg.color}`}>{cfg.label}</span>
      </div>

      {/* Title */}
      <h3 className="text-white font-semibold text-sm mb-2 line-clamp-2">{query}</h3>

      {/* Report snippet */}
      {snippet && (
        <p className="text-white/40 text-xs leading-relaxed line-clamp-4">{snippet}</p>
      )}

      {/* Footer */}
      <div className="mt-3 pt-3 border-t border-white/5 flex items-center justify-between">
        <span className="text-white/20 text-[10px] font-mono">{id.slice(0, 8)}</span>
        <span className="text-indigo-400/60 text-xs">View →</span>
      </div>
    </motion.div>
  );
}
