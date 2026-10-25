import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  Tooltip,
  XAxis,
  YAxis,
  type TooltipProps,
} from 'recharts';
import { api, type Query, type SeriesPoint } from '../api';
import { Chart, Legend } from '../components/Chart';
import { MetricCard } from '../components/MetricCard';
import { gw, mw, pct, signedMw, ukTime } from '../format';
import { useTheme } from '../themeContext';
import { useApi } from '../useApi';

function SeriesTooltip({ active, payload }: TooltipProps<number, string>) {
  const p = payload?.[0]?.payload as SeriesPoint | undefined;
  if (!active || !p) return null;
  return (
    <div className="tooltip">
      <div className="tooltip-title">{ukTime(p.start_time)} UK</div>
      <div>Actual: {mw(p.actual)}</div>
      <div>Forecast: {mw(p.forecast)}</div>
      <div>
        P10–P90: {mw(p.p10)} – {mw(p.p90)}
      </div>
      <div className="muted">
        Published {ukTime(p.publish_time)} · {p.horizon_h != null ? `${p.horizon_h}h ahead` : '–'}
      </div>
    </div>
  );
}

export function DayAheadView({ query }: { query: Query }) {
  const { colors } = useTheme();
  const key = JSON.stringify(query);
  const series = useApi(() => api.series(query), key);
  const metrics = useApi(() => api.metrics(query), key);

  const points = (series.data?.points ?? []).map((p) => ({
    ...p,
    band: p.p10 != null && p.p90 != null ? [p.p10, p.p90] : null,
  }));
  const hasForecast = points.some((p) => p.forecast != null);
  const m = metrics.data?.metrics;
  const subtitle =
    query.mode === 'decision'
      ? `Latest forecast published by ${query.cutoff} UK on the day before delivery`
      : `Latest forecast published at least ${query.horizon}h before each hour`;

  return (
    <>
      <div className="kpis">
        {metrics.error ? (
          <div className="state state-error" role="alert">
            {metrics.error}
          </div>
        ) : (
          <>
            <MetricCard
              label="MAE"
              value={mw(m?.mae)}
              hint={m ? `${pct(m.mae_pct_of_mean_actual)} of mean actual` : ''}
            />
            <MetricCard
              label="Bias (forecast − actual)"
              value={signedMw(m?.bias)}
              hint={m?.pct_over != null ? `Over-forecast ${pct(m.pct_over)} of hours` : ''}
            />
            <MetricCard
              label="P90 absolute error"
              value={mw(m?.p90_abs_error)}
              hint="9 in 10 hours within this"
            />
            <MetricCard
              label="Firm wind (P10)"
              value={mw(m?.firm_wind_p10_mean)}
              hint={m?.forecast_mean != null ? `vs forecast ${mw(m.forecast_mean)}` : ''}
            />
          </>
        )}
      </div>

      <Chart
        title="Actual vs forecast wind generation"
        subtitle={subtitle}
        loading={series.loading}
        error={series.error}
        empty={!hasForecast}
        height={380}
        legend={
          <Legend
            items={[
              { label: 'Actual', color: colors.actual },
              { label: 'Forecast', color: colors.forecast },
              { label: 'P10–P90 band', color: colors.band, kind: 'band' },
            ]}
          />
        }
      >
        <ComposedChart data={points} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
          <CartesianGrid stroke={colors.grid} vertical={false} />
          <XAxis
            dataKey="start_time"
            tickFormatter={ukTime}
            minTickGap={48}
            stroke={colors.axis}
            tick={{ fontSize: 12 }}
          />
          <YAxis tickFormatter={gw} stroke={colors.axis} tick={{ fontSize: 12 }} width={52} />
          <Tooltip content={<SeriesTooltip />} />
          <Area
            dataKey="band"
            stroke="none"
            fill={colors.band}
            fillOpacity={0.35}
            isAnimationActive={false}
            name="P10–P90"
          />
          <Line
            dataKey="forecast"
            stroke={colors.forecast}
            strokeWidth={2}
            dot={false}
            isAnimationActive={false}
          />
          <Line
            dataKey="actual"
            stroke={colors.actual}
            strokeWidth={2}
            dot={false}
            isAnimationActive={false}
          />
        </ComposedChart>
      </Chart>
    </>
  );
}
