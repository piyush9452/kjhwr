import { buildInsights } from '../insights';

const row = (key: number | string, mae: number, bias = 0) => ({
  key,
  n: 10,
  mae,
  rmse: mae,
  bias,
  p90_abs_error: mae,
});

describe('buildInsights', () => {
  it('describes bias direction, horizon growth, worst hour/day and firm wind', () => {
    const lines = buildInsights({
      metrics: {
        n: 100,
        mae: 2000,
        bias: 1500,
        pct_over: 85,
        pct_under: 15,
        mae_pct_of_mean_actual: 18,
        p90_abs_error: 4000,
        firm_wind_p10_mean: 9000,
        forecast_mean: 13000,
      },
      byHorizon: [row(10, 2000), row(0, 1000)],
      byHour: [row(3, 100), row(17, 900)],
      byDay: [
        { ...row('2026-01-05', 500), mean_actual: 1 },
        { ...row('2026-01-20', 3000, -200), mean_actual: 1 },
      ],
    });
    const text = lines.join('\n');
    expect(text).toContain('over-forecast wind in 85% of hours');
    expect(text).toContain('+1,500 MW');
    expect(text).toContain('(+100%)');
    expect(text).toContain('Hour 17:00');
    expect(text).toContain('2026-01-20');
    expect(text).toContain('4,000 MW gap');
  });

  it('handles an empty selection', () => {
    expect(buildInsights({ metrics: { n: 0 }, byHorizon: [], byHour: [], byDay: [] })).toEqual([
      'No matched forecast/actual hours for this selection.',
    ]);
  });
});

describe('gw axis formatter', () => {
  it('keeps half-GW ticks distinct', async () => {
    const { gw } = await import('../format');
    expect([0, 500, 1000, 1500, -3750].map(gw)).toEqual([
      '0 GW',
      '0.5 GW',
      '1 GW',
      '1.5 GW',
      '-3.8 GW',
    ]);
  });
});
