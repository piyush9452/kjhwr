import type { ReactElement, ReactNode } from 'react';
import { ResponsiveContainer } from 'recharts';

interface Props {
  title: string;
  subtitle?: string;
  loading: boolean;
  error: string | null;
  empty: boolean;
  height?: number;
  legend?: ReactNode;
  children: ReactElement;
}

/** Frame for every chart: title, legend and loading / error / empty states. */
export function Chart({
  title,
  subtitle,
  loading,
  error,
  empty,
  height = 320,
  legend,
  children,
}: Props) {
  let body: ReactNode;
  if (error)
    body = (
      <div className="state state-error" role="alert">
        Could not load data. {error}
      </div>
    );
  else if (loading)
    body = (
      <div className="state" aria-busy="true">
        Loading…
      </div>
    );
  else if (empty) body = <div className="state">No data for this selection.</div>;
  else
    body = (
      <ResponsiveContainer width="100%" height={height}>
        {children}
      </ResponsiveContainer>
    );

  return (
    <section className="card chart">
      <header className="chart-header">
        <div>
          <h2>{title}</h2>
          {subtitle && <p className="muted">{subtitle}</p>}
        </div>
        {legend}
      </header>
      <div style={{ minHeight: height }}>{body}</div>
    </section>
  );
}

export function Legend({
  items,
}: {
  items: { label: string; color: string; kind?: 'line' | 'band' }[];
}) {
  return (
    <ul className="legend">
      {items.map((i) => (
        <li key={i.label}>
          <span
            className={i.kind === 'band' ? 'swatch swatch-band' : 'swatch'}
            style={{ background: i.color }}
          />
          {i.label}
        </li>
      ))}
    </ul>
  );
}
