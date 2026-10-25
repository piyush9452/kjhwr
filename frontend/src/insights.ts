import type { DayRow, GroupRow, Metrics } from './api';
import { mw, pct, signedMw } from './format';

export interface InsightInput {
  metrics: Metrics;
  byHorizon: GroupRow[];
  byHour: GroupRow[];
  byDay: DayRow[];
}

const maxBy = <T>(rows: T[], f: (r: T) => number): T | undefined =>
  rows.reduce<T | undefined>(
    (best, r) => (best === undefined || f(r) > f(best) ? r : best),
    undefined,
  );

/** Plain-English takeaways generated from the numbers (no hard-coded findings). */
export function buildInsights({ metrics: m, byHorizon, byHour, byDay }: InsightInput): string[] {
  if (!m.n) return ['No matched forecast/actual hours for this selection.'];
  const out: string[] = [];

  if (m.bias != null && m.pct_over != null) {
    const dir = m.bias > 0 ? 'over-forecast' : 'under-forecast';
    const share = m.bias > 0 ? m.pct_over : (m.pct_under ?? 0);
    out.push(
      `The forecast ${dir} wind in ${pct(share)} of hours, by ${signedMw(m.bias)} on average. ` +
        `Treat the raw forecast as ${m.bias > 0 ? 'optimistic' : 'conservative'} when sizing purchases.`,
    );
  }

  if (m.mae != null && m.mae_pct_of_mean_actual != null) {
    out.push(
      `Typical miss (MAE) is ${mw(m.mae)}, about ${pct(m.mae_pct_of_mean_actual)} of average wind output; ` +
        `9 hours in 10 the miss is within ${mw(m.p90_abs_error)}.`,
    );
  }

  const sorted = [...byHorizon].sort((a, b) => Number(a.key) - Number(b.key));
  if (sorted.length > 1) {
    const first = sorted[0];
    const last = sorted[sorted.length - 1];
    const growth = ((last.mae - first.mae) / first.mae) * 100;
    out.push(
      `Error grows with lead time: MAE is ${mw(first.mae)} at ${first.key}h ahead and ` +
        `${mw(last.mae)} at ${last.key}h ahead (${growth >= 0 ? '+' : ''}${growth.toFixed(0)}%).`,
    );
  }

  const worstHour = maxBy(byHour, (r) => r.mae);
  if (worstHour) {
    out.push(
      `Hour ${String(worstHour.key).padStart(2, '0')}:00 UK is the hardest to forecast (MAE ${mw(worstHour.mae)}).`,
    );
  }

  const worstDay = maxBy(byDay, (r) => r.mae);
  if (worstDay) {
    out.push(
      `Worst delivery day: ${worstDay.key}, with MAE ${mw(worstDay.mae)} and bias ${signedMw(worstDay.bias)}.`,
    );
  }

  if (m.firm_wind_p10_mean != null && m.forecast_mean != null) {
    out.push(
      `Firm wind (P10) averages ${mw(m.firm_wind_p10_mean)} against a forecast of ${mw(m.forecast_mean)}. ` +
        `Cover the ${mw(m.forecast_mean - m.firm_wind_p10_mean)} gap with day-ahead purchases or flexible options.`,
    );
  }
  return out;
}
