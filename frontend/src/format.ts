const nf = new Intl.NumberFormat('en-GB', { maximumFractionDigits: 0 });

export const mw = (v: number | null | undefined): string =>
  v == null ? '–' : `${nf.format(v)} MW`;

export const signedMw = (v: number | null | undefined): string =>
  v == null ? '–' : `${v > 0 ? '+' : ''}${nf.format(v)} MW`;

export const pct = (v: number | null | undefined, digits = 0): string =>
  v == null ? '–' : `${v.toFixed(digits)}%`;

const gwFmt = new Intl.NumberFormat('en-GB', { maximumFractionDigits: 1 });

/** Axis label in GW; keeps one decimal so 0.5 GW ticks don't collapse into duplicate labels. */
export const gw = (v: number): string => `${gwFmt.format(v / 1000)} GW`;

const timeFmt = new Intl.DateTimeFormat('en-GB', {
  timeZone: 'Europe/London',
  day: '2-digit',
  month: 'short',
  hour: '2-digit',
  minute: '2-digit',
});

/** Format a UTC ISO timestamp in UK local time. */
export const ukTime = (iso: string | null | undefined): string =>
  iso ? timeFmt.format(new Date(iso)) : '–';
