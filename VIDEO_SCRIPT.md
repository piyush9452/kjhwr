# Video script: Wind Forecast Desk (≤ 10 minutes)

Timings are targets. **[SCREEN]** lines say what to show, and the rest is spoken.
All numbers are January 2026 decisions using the D-1 09:00 forecast. Re-check them in the app before recording.

---

## Part 1: Client pitch (≈ 5:00)

### 0:00 – 0:45 · The problem
**[SCREEN]** App home page, Day-ahead view, whole month selected.

> Every morning your desk decides how much power to buy in the day-ahead auction for tomorrow. Wind is the biggest swing factor in that decision. Today you look at the latest national wind forecast and buy the gap.
>
> Two questions are hard to answer with that workflow. First, *which* forecast did we actually have at decision time? Second, how much should we trust it? If the forecast says 13 GW and only 11 GW turns up, you are short and buying back in the balancing market at a premium.

### 0:45 – 2:30 · Live demo: Day-ahead view
**[SCREEN]** Pick a single delivery day, e.g. 10 January. Hover the chart.

> This is one delivery day. Orange is what wind actually produced. Blue is the forecast you had at 9 am the day before: not a later, better one, but the one you could actually trade on. Hover any hour and you see when that forecast was published, here 07:30 the previous morning, and how far ahead it was looking.
>
> The shaded band is the realistic range. It's built from how wrong this forecast has actually been at the same lead time. The bottom of the band is the P10: nine times in ten, wind delivered at least that much.

**[SCREEN]** Toggle to *Fixed horizon*, drag the slider from 0 to 40h.

> If you want to know how much better a later forecast would be, switch to horizon mode and drag. The error shrinks as you get closer to delivery, but you can't trade on the forecast that arrives after gate closure.

**[SCREEN]** Back to decision mode, select the whole month. Point at the KPI cards.

### 2:30 – 3:45 · Key accuracy findings
**[SCREEN]** Forecast accuracy page. Point at the insights panel, then the charts.

> Across January the picture is very clear.
>
> - **The forecast is optimistic.** It over-forecast wind in about **85% of hours**, by about **+1.7 GW** on average. That's not random noise. It's a consistent bias you can correct for.
> - **The typical miss is about 2 GW**, roughly 18% of average wind output. Nine hours in ten, the miss is within about **4.1 GW**.
> - **Error grows with lead time.** A same-day forecast misses by about 1.7 GW, while the day-ahead forecast you trade on misses by about 2 GW.
> - The histogram shows the shape: most of the mass sits to the right of zero, so you are rarely surprised by *more* wind.

### 3:45 – 5:00 · How this cuts procurement risk and cost
**[SCREEN]** Day-ahead view, KPI "Firm wind (P10)".

> So here's how to use it. Over January the forecast averaged about **13 GW**, but the wind you could count on nine times in ten, the P10, was about **9 GW**.
>
> Today you would buy as if 13 GW will show up. With this tool you size your firm day-ahead purchase against the P10, then cover the gap between P10 and the forecast with cheaper, flexible options. The bias correction alone moves about 1.7 GW out of expensive imbalance exposure and into planned, priced purchases.
>
> The pilot runs on official Elexon data, refreshes with one command, and every number on screen can be traced back to code and tests. The next step is to run it on a rolling window, so the bands are always calibrated on the most recent weeks.

---

## Part 2: Tech-lead walkthrough (≈ 5:00)

### 5:00 – 5:45 · Architecture
**[SCREEN]** README Mermaid diagram.

> It's a three-layer Python backend and a React front end. An Elexon client fetches the FUELHH and WINDFOR streams with timeouts and retries. The stream endpoints have no paging cursor, so we paginate by date windows. Ingestion cleans the data and writes a versioned, gzipped snapshot of about 50 kB into `data/`. The FastAPI app only ever reads that snapshot, so the demo is fast and survives a BMRS outage.

### 5:45 – 6:45 · Data pipeline and data quality
**[SCREEN]** `backend/app/ingest.py`, then the notebook's data-quality cell.

> Three things mattered here.
>
> - **Resolution.** WINDFOR is hourly and FUELHH is half-hourly, so we average each pair of half-hours to an hour. That conserves energy, and hours missing a half are dropped, never half-filled.
> - **Duplicates and gaps.** We de-duplicate on start time, keeping the latest publish, and log missing half-hours and days that don't have 48 periods, which would flag a DST change. January came back clean: 1,488 half-hours, no gaps, 264 forecast runs.
> - **Time zones.** Everything is UTC internally. We convert to Europe/London only to decide which delivery day an hour belongs to, and there's a BST unit test.

### 6:45 – 7:45 · Forecast selection logic
**[SCREEN]** `backend/app/analytics.py`: `cutoff_utc`, `select_decision`, `select_horizon`.

> Horizon is start time minus publish time. Decision mode builds a per-row cutoff, D-1 at 09:00 London converted to UTC, keeps runs published at or before it, and takes the latest per target hour. Horizon mode keeps runs at least H hours old and takes the latest. Anything outside 0 to 48 hours is dropped at ingestion.
>
> One finding from the data: WINDFOR publishes about eight runs a day, at irregular times. With a 09:00 cutoff you get the 07:30 run, and there's a 09:30 run *after* the cutoff but before N2EX gate closure at 09:50. The notebook quantifies whether moving the cutoff is worth it: waiting for the 09:30 run only improves MAE by about 26 MW, so 09:00 is the safer choice.

### 7:45 – 8:30 · Metrics and bands
**[SCREEN]** `metrics()` and `apply_bands()`, then the matching tests in `test_analytics.py`.

> Error is forecast minus actual. We report MAE, RMSE, bias, P50/P90/P99 absolute error, and the over/under split. We don't use MAPE, because wind goes near zero, so we report MAE as a percentage of mean actual instead. Bands come from empirical error quantiles per six-hour horizon bucket. Note the flip: P10 of *actual* is the forecast minus the *90th* percentile of error. Each of these has a tiny hand-computed test.

### 8:30 – 9:15 · Front end, testing, CI, Docker, deployment
**[SCREEN]** `frontend/src/api.ts`, `components/`, then the GitHub Actions run, then `docker compose up`.

> The front end has one API client, three reusable components (Chart, MetricCard and Controls), two pages, and light and dark themes. Every chart handles loading, empty and error states. The insights text is generated from the numbers, not hard-coded.
>
> CI runs ruff, pytest with an 80% coverage gate (we're at 99%), executes the notebook, then ESLint, the TypeScript type-check, Prettier, vitest and the Vite build, and finally brings the Docker stack up and smoke-tests it. `docker compose up` runs the whole stack locally. On Vercel the React build is static, and FastAPI runs as a Python serverless function under `/api`.

### 9:15 – 9:50 · Trade-offs
> - A snapshot instead of live calls: reproducible and robust, but needs a refresh job in production.
> - Gzipped JSON instead of Parquet: it keeps pyarrow out of the serverless bundle, and at this size the difference doesn't matter.
> - In-sample bands: the app fits them on the same month. The notebook back-tests that by fitting on the first half of January only, and P10 still held for 91% of hours in the second half, so they're not just flattering themselves. Production should still fit on a strictly earlier rolling window.
> - Curtailment: some of the over-forecast bias is probably curtailment, not forecast error. Separating the two needs constraint data, which is the natural next phase.
>
> Thanks. Everything's in the repo, including the notebook with the full analysis.
