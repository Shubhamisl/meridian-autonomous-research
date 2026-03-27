interface PipelineTimelineProps {
  phases: string[];
  currentPhase: string | null;
}

function formatPhaseLabel(phase: string) {
  return phase
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export default function PipelineTimeline({ phases, currentPhase }: PipelineTimelineProps) {
  const timelinePhases = phases.length > 0 ? phases : [];
  const currentIndex =
    currentPhase && timelinePhases.length > 0
      ? timelinePhases.findIndex((phase) => phase.toLowerCase() === currentPhase.toLowerCase())
      : -1;
  const hasPhases = timelinePhases.length > 0;

  return (
    <section className="mb-10">
      {hasPhases ? (
        <div className="overflow-x-auto pb-1">
          <div className="flex min-w-[720px] items-start gap-0">
            {timelinePhases.map((phase, index) => {
              const isCurrent = currentIndex === index;
              const isComplete = currentIndex >= 0 && index < currentIndex;
              const active = isCurrent || isComplete;
              const connectorActive = currentIndex > index;

              return (
                <div className="flex flex-1 items-start gap-0" key={phase}>
                  <div className="flex flex-col items-center gap-3">
                    <div
                      className={`flex h-9 w-9 items-center justify-center rounded-full text-[11px] font-semibold ${
                        isCurrent
                          ? 'bg-teal text-white shadow-soft'
                          : active
                            ? 'bg-teal/15 text-teal'
                            : 'bg-fog/60 text-slate/60'
                      }`}
                    >
                      {String(index + 1).padStart(2, '0')}
                    </div>
                    <span
                      className={`text-[11px] font-semibold uppercase tracking-[0.16em] ${
                        active ? 'text-teal' : 'text-slate/55'
                      }`}
                    >
                      {formatPhaseLabel(phase)}
                    </span>
                  </div>
                  {index < timelinePhases.length - 1 && (
                    <div className={`mt-4 h-px flex-1 ${connectorActive ? 'bg-teal/25' : 'bg-fog/70'}`} />
                  )}
                </div>
              );
            })}
          </div>
        </div>
      ) : (
        <div className="rounded-[1.5rem] border border-fog/60 bg-white/80 p-5 text-sm leading-7 text-slate/68 shadow-soft">
          Pipeline phases were not returned with this workspace payload yet.
        </div>
      )}

      <p className="mt-4 text-sm leading-7 text-slate/65">
        {currentPhase
          ? currentIndex >= 0
            ? `Current phase: ${formatPhaseLabel(currentPhase)}`
            : `Current phase: ${formatPhaseLabel(currentPhase)} (not found in the returned phase list)`
          : 'Current phase was not returned in the workspace payload.'}
      </p>
    </section>
  );
}
