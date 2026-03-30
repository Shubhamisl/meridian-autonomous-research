export const RESEARCH_MODES = ['Biomedical', 'Intelligence', 'Market', 'Legal', 'General'] as const;

export type ResearchMode = (typeof RESEARCH_MODES)[number];

export const MODE_PROMPTS: Record<ResearchMode, string> = {
  Biomedical: 'Summarize the latest evidence on GLP-1 agonists and long-term metabolic outcomes.',
  Intelligence: 'Produce a threat brief on recent ransomware actors targeting healthcare networks.',
  Market: 'Analyze how GLP-1 adoption could reshape the global packaged snacks market.',
  Legal: 'Review current AI regulation trends affecting foundation model deployment in the EU.',
  General: 'Research the most important facts, tradeoffs, and recent developments for my topic.',
};

export function modeFromDomain(domain: string | null | undefined): ResearchMode {
  switch (domain) {
    case 'biomedical':
      return 'Biomedical';
    case 'computer_science':
      return 'Intelligence';
    case 'economics':
      return 'Market';
    case 'legal':
      return 'Legal';
    default:
      return 'General';
  }
}
