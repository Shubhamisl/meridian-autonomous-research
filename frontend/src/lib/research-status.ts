const STATUS_META = {
  pending: {
    label: 'Queued',
    pillClassName: 'bg-amber/10 text-amber',
    emphasis: 'Meridian has accepted the inquiry and is preparing the research pipeline.',
  },
  running: {
    label: 'In Progress',
    pillClassName: 'bg-teal/10 text-teal',
    emphasis: 'Meridian is actively gathering and synthesizing evidence for this inquiry.',
  },
  completed: {
    label: 'Complete',
    pillClassName: 'bg-teal-soft text-teal',
    emphasis: 'The report is ready for review.',
  },
  failed: {
    label: 'Needs Attention',
    pillClassName: 'bg-rose/10 text-rose',
    emphasis: 'The inquiry was interrupted before Meridian could finish the report.',
  },
} as const;

export function getStatusMeta(status: string) {
  return STATUS_META[status as keyof typeof STATUS_META] ?? STATUS_META.pending;
}

export function formatStatusLabel(status: string) {
  return getStatusMeta(status).label;
}
