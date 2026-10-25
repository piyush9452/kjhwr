import { api, DEFAULT_QUERY, UNAVAILABLE_MSG } from '../api';

describe('api client', () => {
  afterEach(() => vi.restoreAllMocks());

  it('sends the query as URL params', async () => {
    const fetchMock = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValue(new Response(JSON.stringify({ rows: [] }), { status: 200 }));
    await api.byHour(DEFAULT_QUERY);
    const url = String(fetchMock.mock.calls[0][0]);
    expect(url).toContain('/api/accuracy/by-hour?');
    expect(url).toContain('start=2026-01-10');
    expect(url).toContain('mode=decision');
    expect(url).toContain('cutoff=09%3A00');
  });

  it('surfaces the backend error detail', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ detail: 'start must be on or before end' }), { status: 422 }),
    );
    await expect(api.series(DEFAULT_QUERY)).rejects.toThrow('422: start must be on or before end');
  });

  it('shows a friendly message when the backend is down or unreachable', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response('<html>Bad Gateway</html>', { status: 502 }),
    );
    await expect(api.metrics(DEFAULT_QUERY)).rejects.toThrow(`${UNAVAILABLE_MSG} (HTTP 502)`);

    vi.spyOn(globalThis, 'fetch').mockRejectedValueOnce(new TypeError('Failed to fetch'));
    await expect(api.metrics(DEFAULT_QUERY)).rejects.toThrow(UNAVAILABLE_MSG);
  });
});
