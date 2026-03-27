const PHASES = ['Classify', 'Collect', 'Score', 'Chunk', 'Retrieve', 'Synthesize'];

interface PipelineTimelineProps {
  status: string;
}

export default function PipelineTimeline({ status }: PipelineTimelineProps) {
  const activeCount = status === 'completed' ? PHASES.length : status === 'running' ? 4 : 1;

  return (
    <section className="mb-10 overflow-x-auto">
      <div className="flex min-w-[720px] items-start gap-0">
        {PHASES.map((phase, index) => {
          const active = index < activeCount;

          return (
            <div className="flex flex-1 items-start gap-0" key={phase}>
              <div className="flex flex-col items-center gap-3">
                <div
                  className={`flex h-9 w-9 items-center justify-center rounded-full text-[11px] font-semibold ${
                    active ? 'bg-teal text-white' : 'bg-fog/60 text-slate/60'
                  }`}
                >
                  {String(index + 1).padStart(2, '0')}
                </div>
                <span
                  className={`text-[11px] font-semibold uppercase tracking-[0.16em] ${
                    active ? 'text-teal' : 'text-slate/55'
                  }`}
                >
                  {phase}
                </span>
              </div>
              {index < PHASES.length - 1 && (
                <div className={`mt-4 h-px flex-1 ${active ? 'bg-teal/25' : 'bg-fog/70'}`} />
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}
