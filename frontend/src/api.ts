// Single API client: every backend call and response type lives here.

export type Mode = 'decision' | 'horizon';

export interface Query {
  start: string;
  end: string;
  mode: Mode;
  horizon: number;
  cutoff: string;
}

export interface SeriesPoint {
  start_time: string;
  actual: number | null;
  forecast: number | null;
  publish_time: string | null;
  horizon_h: number | null;
  p10: number | null;
  p50: number | null;
  p90: number | null;
}

export interface SeriesResponse {
  mode: Mode;
  cutoff: string | null;
  horizon_h: number | null;
  points: SeriesPoint[];
}

export interface Metrics {
  n: number;
  mae?: number | null;
  rmse?: number | null;
  bias?: number | null;
  mean_actual?: number | null;
  mae_pct_of_mean_actual?: number | null;
  pct_over?: number | null;
  pct_under?: number | null;
  p50_abs_error?: number | null;
  p90_abs_error?: number | null;
  p99_abs_error?: number | null;
  firm_wind_p10_mean?: number | null;
  firm_wind_p10_min?: number | null;
  forecast_mean?: number | null;
}

export interface GroupRow {
  key: number | string;
  n: number;
  mae: number;
  rmse: number;
  bias: number;
  p90_abs_error: number;
}

export interface DayRow extends GroupRow {
  mean_actual: number;
}

export interface MetricsResponse {
  mode: Mode;
  metrics: Metrics;
  by_day: DayRow[];
}

export interface GroupResponse {
  rows: GroupRow[];
}

export interface HistogramBin {
  bin_start: number;
  bin_end: number;
  count: number;
}

export interface DistributionResponse {
  bins: HistogramBin[];
  pct_over: number | null;
  pct_under: number | null;
  n: number;
}

export interface Health {
  status: 'ok';
  snapshot_version: string;
  fetched_at: string;
  delivery_start: string;
  delivery_end: string;
}

export const DELIVERY_START = '2026-01-02';
export const DELIVERY_END = '2026-02-01';
export const MAX_HORIZON_H = 48;

export const DEFAULT_QUERY: Query = {
  start: '2026-01-10',
  end: '2026-01-12',
  mode: 'decision',
  horizon: 24,
  cutoff: '09:00',
};

const BASE = import.meta.env.VITE_API_BASE ?? '';

export class ApiError extends Error {}

// Generous enough for a serverless cold start, short enough not to spin forever.
const REQUEST_TIMEOUT_MS = 30_000;

export const UNAVAILABLE_MSG =
  'The data service is unavailable right now. Please try again in a moment.';

async function get<T>(path: string, q?: Query): Promise<T> {
  const params = q
    ? '?' +
      new URLSearchParams({
        start: q.start,
        end: q.end,
        mode: q.mode,
        horizon: String(q.horizon),
        cutoff: q.cutoff,
      }).toString()
    : '';
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}${params}`, {
      signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
    });
  } catch {
    // Network failure or timeout (backend down, offline, DNS): no response to read.
    throw new ApiError(UNAVAILABLE_MSG);
  }
  // 5xx bodies come from the proxy (nginx/Vite/Vercel), not our API, so don't show them.
  if (res.status >= 500) throw new ApiError(`${UNAVAILABLE_MSG} (HTTP ${res.status})`);
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    const detail = body?.detail;
    const msg = typeof detail === 'string' ? detail : (detail?.[0]?.msg ?? res.statusText);
    throw new ApiError(`${res.status}: ${msg}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => get<Health>('/api/health'),
  series: (q: Query) => get<SeriesResponse>('/api/series', q),
  metrics: (q: Query) => get<MetricsResponse>('/api/metrics', q),
  byHorizon: (q: Query) => get<GroupResponse>('/api/accuracy/by-horizon', q),
  byHour: (q: Query) => get<GroupResponse>('/api/accuracy/by-hour', q),
  distribution: (q: Query) => get<DistributionResponse>('/api/accuracy/distribution', q),
};
