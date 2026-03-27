import { Activity, FlaskConical, Gavel, ShieldAlert, TrendingUp } from 'lucide-react';

interface StarterModesProps {
  onSelectPrompt: (value: string) => void;
}

const MODES = [
  {
    title: 'Biomedical Review',
    description: 'Trace recent trial outcomes, unresolved evidence gaps, and high-signal literature.',
    icon: FlaskConical,
    prompt: 'Summarize the latest evidence on GLP-1 agonists and long-term metabolic outcomes.',
  },
  {
    title: 'Threat Intelligence',
    description: 'Map adversaries, incidents, vulnerabilities, and operational implications.',
    icon: ShieldAlert,
    prompt: 'Produce a threat brief on recent ransomware actors targeting healthcare networks.',
  },
  {
    title: 'Market Analysis',
    description: 'Compare demand shifts, strategic moats, and signals that matter for decision-makers.',
    icon: TrendingUp,
    prompt: 'Analyze how GLP-1 adoption could reshape the global packaged snacks market.',
  },
  {
    title: 'Legal Landscape',
    description: 'Synthesize regulatory movement, precedents, and compliance implications.',
    icon: Gavel,
    prompt: 'Review current AI regulation trends affecting foundation model deployment in the EU.',
  },
];

export default function StarterModes({ onSelectPrompt }: StarterModesProps) {
  return (
    <section className="mb-16">
      <div className="mb-7 flex items-end justify-between">
        <div>
          <div className="section-label">Guided Intelligence</div>
          <h2 className="mt-2 font-serif text-3xl font-semibold tracking-tight text-ink">
            Specialized frameworks
          </h2>
        </div>
        <div className="hidden items-center gap-2 text-sm text-slate/55 md:flex">
          <Activity className="h-4 w-4" />
          <span>Use a framework as your starting point</span>
        </div>
      </div>

      <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-4">
        {MODES.map((mode) => {
          const Icon = mode.icon;
          return (
            <button
              key={mode.title}
              className="rounded-2xl border border-fog/60 bg-white/86 p-6 text-left shadow-soft transition hover:-translate-y-1 hover:border-teal/30 hover:shadow-panel"
              onClick={() => onSelectPrompt(mode.prompt)}
            >
              <Icon className="h-8 w-8 text-teal" />
              <h3 className="mt-6 font-serif text-2xl font-semibold tracking-tight text-ink">
                {mode.title}
              </h3>
              <p className="mt-3 text-sm leading-7 text-slate/70">{mode.description}</p>
            </button>
          );
        })}
      </div>
    </section>
  );
}
