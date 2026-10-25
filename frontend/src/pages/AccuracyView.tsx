import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ReferenceLine,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { api, type HistogramBin, type Query } from '../api';
import { Chart, Legend } from '../components/Chart';
import { MetricCard } from '../components/MetricCard';
import { gw, mw, pct } from '../format';
import { buildInsights } from '../insights';
import { useTheme } from '../themeContext';
import { useApi } from '../useApi';

const mwTooltip = (v: number) => mw(v);

export function AccuracyView({ query }: { query: Query }) {
  const { colors } = useTheme();
  const key = JSON.stringify(query);
  const byHorizon = useApi(() => api.byHorizon(query), key);
  const byHour = useApi(() => api.byHour(query), key);
  const dist = useApi(() => api.distribution(query), key);
  const metrics = useApi(() => api.metrics(query), key);

  const axis = { stroke: colors.axis, tick: { fontSize: 12 } };
  const tooltipStyle = {
    contentStyle: { background: colors.surface, borderColor: colors.grid, color: colors.text },
  };
  const bins = (dist.data?.bins ?? []).map((b: HistogramBin) => ({
    ...b,
    mid: (b.bin_start + b.bin_end) / 2,
  }));
  const insights =
    metrics.data && byHorizon.data && byHour.data
      ? buildInsights({
          metrics: metrics.data.metrics,
          byHorizon: byHorizon.data.rows,
          byHour: byHour.data.rows,
          byDay: metrics.data.by_day,
        })
      : [];

  return (
    <>
      <section className="card insights" aria-live="polite">
        <h2>Insights</h2>
        {metrics.error ? (
          <div className="state state-error" role="alert">
            {metrics.error}
          </div>
        ) : insights.length ? (
          <ul>
            {insights.map((s) => (
              <li key={s}>{s}</li>
            ))}
          </ul>
        ) : (
          <div className="state">Loading…</div>
        )}
      </section>

      <div className="grid-2">
        <Chart
          title="Error vs forecast horizon"
          subtitle="Every forecast run vs actual, by hours between publish and delivery"
          loading={byHorizon.loading}
          error={byHorizon.error}
          empty={!byHorizon.data?.rows.length}
          legend={
            <Legend
              items={[
                { label: 'MAE', color: colors.forecast },
                { label: 'Bias', color: colors.actual },
              ]}
            />
          }
        >
          <LineChart
            data={byHorizon.data?.rows}
            margin={{ top: 8, right: 16, bottom: 16, left: 0 }}
          >
            <CartesianGrid stroke={colors.grid} vertical={false} />
            <XAxis
              dataKey="key"
              {...axis}
              label={{ value: 'Horizon (h)', position: 'insideBottom', offset: -8 }}
            />
            <YAxis tickFormatter={gw} {...axis} width={52} />
            <ReferenceLine y={0} stroke={colors.axis} />
            <Tooltip
              formatter={mwTooltip}
              labelFormatter={(h) => `${h}h ahead`}
              {...tooltipStyle}
            />
            <Line
              dataKey="mae"
              name="MAE"
              stroke={colors.forecast}
              strokeWidth={2}
              dot={false}
              isAnimationActive={false}
            />
            <Line
              dataKey="bias"
              name="Bias"
              stroke={colors.actual}
              strokeWidth={2}
              dot={false}
              isAnimationActive={false}
            />
          </LineChart>
        </Chart>

        <Chart
          title="Error by hour of day"
          subtitle="Mean absolute error of the selected forecast, by UK hour"
          loading={byHour.loading}
          error={byHour.error}
          empty={!byHour.data?.rows.length}
        >
          <BarChart data={byHour.data?.rows} margin={{ top: 8, right: 16, bottom: 16, left: 0 }}>
            <CartesianGrid stroke={colors.grid} vertical={false} />
            <XAxis
              dataKey="key"
              {...axis}
              label={{ value: 'Hour (UK)', position: 'insideBottom', offset: -8 }}
            />
            <YAxis tickFormatter={gw} {...axis} width={52} />
            <Tooltip
              formatter={mwTooltip}
              labelFormatter={(h) => `${String(h).padStart(2, '0')}:00`}
              {...tooltipStyle}
            />
            <Bar
              dataKey="mae"
              name="MAE"
              fill={colors.forecast}
              radius={[4, 4, 0, 0]}
              isAnimationActive={false}
            />
          </BarChart>
        </Chart>

        <Chart
          title="Error distribution"
          subtitle="Forecast − actual; right of zero means the forecast was too high"
          loading={dist.loading}
          error={dist.error}
          empty={!bins.length}
          legend={
            <Legend
              items={[
                { label: 'Under-forecast', color: colors.actual },
                { label: 'Over-forecast', color: colors.forecast },
              ]}
            />
          }
        >
          <BarChart
            data={bins}
            margin={{ top: 8, right: 16, bottom: 16, left: 0 }}
            barCategoryGap={1}
          >
            <CartesianGrid stroke={colors.grid} vertical={false} />
            <XAxis dataKey="mid" tickFormatter={gw} {...axis} />
            <YAxis allowDecimals={false} {...axis} width={40} />
            <Tooltip
              formatter={(v: number) => [`${v} hours`, 'Count']}
              labelFormatter={(_, p) => {
                const b = p?.[0]?.payload as HistogramBin | undefined;
                return b ? `${mw(b.bin_start)} to ${mw(b.bin_end)}` : '';
              }}
              {...tooltipStyle}
            />
            <Bar dataKey="count" radius={[4, 4, 0, 0]} isAnimationActive={false}>
              {bins.map((b) => (
                <Cell key={b.bin_start} fill={b.mid >= 0 ? colors.forecast : colors.actual} />
              ))}
            </Bar>
          </BarChart>
        </Chart>

        <section className="card">
          <h2>Over vs under-forecast</h2>
          <p className="muted">
            Share of hours where the selected forecast was above or below actual
          </p>
          {dist.data && dist.data.n > 0 ? (
            <>
              <div className="split-bar" aria-hidden="true">
                <span style={{ width: `${dist.data.pct_over}%`, background: colors.forecast }} />
                <span style={{ width: `${dist.data.pct_under}%`, background: colors.actual }} />
              </div>
              <div className="kpis kpis-2">
                <MetricCard
                  label="Over-forecast"
                  value={pct(dist.data.pct_over)}
                  hint="Forecast above actual"
                />
                <MetricCard
                  label="Under-forecast"
                  value={pct(dist.data.pct_under)}
                  hint="Forecast below actual"
                />
              </div>
            </>
          ) : (
            <div className="state">
              {dist.error ?? (dist.loading ? 'Loading…' : 'No data for this selection.')}
            </div>
          )}
        </section>
      </div>
    </>
  );
}
