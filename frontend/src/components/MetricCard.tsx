interface Props {
  label: string;
  value: string;
  hint?: string;
}

export function MetricCard({ label, value, hint }: Props) {
  return (
    <div className="metric-card" role="group" aria-label={label}>
      <div className="metric-label">{label}</div>
      <div className="metric-value">{value}</div>
      {hint && <div className="metric-hint">{hint}</div>}
    </div>
  );
}
