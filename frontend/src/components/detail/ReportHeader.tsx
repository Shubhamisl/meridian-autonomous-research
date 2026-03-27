import { formatStatusLabel, getStatusMeta } from '../../lib/research-status';

interface ReportHeaderProps {
  jobId: string;
  query: string;
  status: string;
}

export default function ReportHeader({ jobId, query, status }: ReportHeaderProps) {
  const statusMeta = getStatusMeta(status);

  return (
    <section className="mb-10">
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <span className={`status-pill ${statusMeta.pillClassName}`}>{formatStatusLabel(status)}</span>
        <span className="status-pill bg-white text-slate/65">Job {jobId.slice(0, 8)}</span>
        <span className="status-pill bg-white text-slate/65">Domain autodetected</span>
        <span className="status-pill bg-white text-slate/65">Format selected at runtime</span>
      </div>

      <h1 className="max-w-4xl font-serif text-5xl font-semibold leading-[1.08] tracking-tight text-ink md:text-6xl">
        {query}
      </h1>
      <p className="mt-5 max-w-3xl text-base leading-7 text-slate/72">{statusMeta.emphasis}</p>
    </section>
  );
}
