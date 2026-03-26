import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, Loader2, ArrowRight, BrainCircuit } from 'lucide-react';
import ReportViewer from './ReportViewer';

export default function Dashboard() {
  const [query, setQuery] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [report, setReport] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let interval: number;
    
    if (jobId && !report && !error) {
      interval = setInterval(async () => {
        try {
          const res = await fetch(`/research/${jobId}`);
          if (!res.ok) throw new Error('Failed to fetch status');
          const data = await res.json();
          
          if (data.status === 'completed') {
            const reportRes = await fetch(`/research/${jobId}/report`);
            if (reportRes.ok) {
              const reportData = await reportRes.json();
              setReport(reportData);
              setIsSubmitting(false);
            }
          } else if (data.status === 'failed') {
            setError('Research intelligence engine encountered an exception.');
            setIsSubmitting(false);
          }
        } catch (e) {
          console.error(e);
        }
      }, 5000);
    }
    
    return () => clearInterval(interval);
  }, [jobId, report, error]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    
    setIsSubmitting(true);
    setError(null);
    setReport(null);
    setJobId(null);
    
    try {
      const res = await fetch('/research/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query }),
      });
      
      if (!res.ok) throw new Error('Failed to start research');
      const data = await res.json();
      setJobId(data.id);
    } catch (e) {
      setError('Unable to reach Meridian core systems.');
      setIsSubmitting(false);
    }
  };

  return (
    <div className="w-full flex justify-center">
      <div className="w-full space-y-8 transition-all duration-700">
        {/* Main Input Card */}
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.1, ease: 'easeOut' }}
          className="glass-panel rounded-3xl p-8 relative overflow-hidden group"
        >
          <div className="absolute inset-0 bg-gradient-to-r from-white/0 via-white/5 to-white/0 translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-1000 ease-in-out pointer-events-none" />
          
          <div className="max-w-2xl mx-auto text-center space-y-8 relative z-10">
            <div className={`space-y-4 transition-all duration-700 ${jobId || report ? 'scale-90 opacity-80' : 'scale-100'}`}>
              <h2 className="text-4xl md:text-5xl font-bold tracking-tight">
                What shall we <span className="text-gradient-accent">research?</span>
              </h2>
              <p className="text-lg text-zinc-400 font-light max-w-xl mx-auto leading-relaxed">
                Enter a topic and Meridian will autonomously orchestrate internet searches, academic papers, and synthesize a comprehensive report.
              </p>
            </div>

            <form onSubmit={handleSubmit} className="relative w-full group">
              <div className="absolute inset-y-0 left-6 flex items-center pointer-events-none">
                <Search className="h-5 w-5 text-zinc-400 group-focus-within:text-accent transition-colors duration-300" />
              </div>
              
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="e.g. 'Recent breakthroughs in solid-state quantum batteries...'"
                className="w-full h-16 pl-14 pr-32 bg-zinc-900/50 backdrop-blur-md border border-white/10 rounded-2xl text-lg text-white placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent/50 transition-all duration-300 shadow-inner"
                disabled={isSubmitting && !report}
              />
              
              <div className="absolute inset-y-2 right-2 flex items-center">
                <button
                  type="submit"
                  disabled={!query.trim() || (isSubmitting && !report)}
                  className="h-full px-6 bg-white text-black font-semibold rounded-xl hover:bg-zinc-200 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-300 flex items-center gap-2 transform active:scale-95"
                >
                  {isSubmitting && !report ? (
                    <Loader2 className="w-5 h-5 animate-spin" />
                  ) : (
                    <>
                      <span>Commence</span>
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </button>
              </div>
            </form>
            
            {error && (
              <p className="text-red-400 text-sm mt-4 bg-red-400/10 py-2 rounded-lg border border-red-400/20">{error}</p>
            )}
          </div>
        </motion.div>

        {/* Status Panel (appears when job is running) */}
        <AnimatePresence>
          {jobId && !report && !error && (
            <motion.div
              initial={{ opacity: 0, height: 0, y: -20 }}
              animate={{ opacity: 1, height: 'auto', y: 0 }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.5, ease: 'easeInOut' }}
              className="glass rounded-2xl p-6 border-accent/20 max-w-2xl mx-auto"
            >
              <div className="flex items-start gap-4">
                <div className="w-12 h-12 rounded-full bg-accent/10 flex items-center justify-center border border-accent/20 shrink-0">
                  <BrainCircuit className="w-6 h-6 text-accent animate-pulse" />
                </div>
                <div className="space-y-2 w-full">
                  <div className="flex justify-between items-center">
                    <h3 className="text-xl font-semibold text-white">Synthesizing Intelligence...</h3>
                    <span className="text-xs font-mono text-zinc-400 bg-zinc-900/50 px-2 py-1 rounded-md border border-white/5">
                      JOB ID: {jobId.split('-')[0].toUpperCase()}
                    </span>
                  </div>
                  
                  <div className="space-y-4 pt-2">
                    <div className="flex items-center gap-3 text-sm text-zinc-400">
                      <Loader2 className="w-4 h-4 animate-spin text-accent" />
                      <span>Orchestrating autonomous agents across Wikipedia & ArXiv. Searching DuckDuckGo for context.</span>
                    </div>
                    
                    {/* Pulsing Loading Bar */}
                    <div className="w-full h-1.5 bg-zinc-800/50 rounded-full overflow-hidden">
                      <motion.div 
                        className="h-full bg-gradient-to-r from-accent via-fuchsia-500 to-blue-500 rounded-full w-full opacity-50"
                        animate={{ x: ["-100%", "100%"] }}
                        transition={{ repeat: Infinity, duration: 2, ease: "linear" }}
                      />
                    </div>
                  </div>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Report Output */}
        <AnimatePresence>
          {report && (
            <ReportViewer report={report} />
          )}
        </AnimatePresence>

      </div>
    </div>
  );
}
