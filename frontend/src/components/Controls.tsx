import { DELIVERY_END, DELIVERY_START, MAX_HORIZON_H, type Mode, type Query } from '../api';

interface Props {
  query: Query;
  onChange: (q: Query) => void;
}

export function Controls({ query, onChange }: Props) {
  const set = (patch: Partial<Query>) => onChange({ ...query, ...patch });

  return (
    <div className="controls card" role="group" aria-label="Filters">
      <label>
        Delivery date
        <input
          type="date"
          min={DELIVERY_START}
          max={DELIVERY_END}
          value={query.start}
          onChange={(e) => {
            const v = e.target.value;
            // Keep the range valid: moving start past end drags end along.
            if (v) set({ start: v, end: query.end < v ? v : query.end });
          }}
        />
      </label>
      <label>
        to
        <input
          type="date"
          aria-label="End date"
          min={query.start}
          max={DELIVERY_END}
          value={query.end}
          onChange={(e) => e.target.value && set({ end: e.target.value })}
        />
      </label>
      <button
        type="button"
        className="link"
        onClick={() => set({ start: DELIVERY_START, end: DELIVERY_END })}
      >
        Whole month
      </button>

      <div className="segmented" role="radiogroup" aria-label="Forecast selection mode">
        {(['decision', 'horizon'] as Mode[]).map((m) => (
          <button
            key={m}
            type="button"
            role="radio"
            aria-checked={query.mode === m}
            className={query.mode === m ? 'active' : ''}
            onClick={() => set({ mode: m })}
          >
            {m === 'decision' ? 'Decision cutoff' : 'Fixed horizon'}
          </button>
        ))}
      </div>

      {query.mode === 'decision' ? (
        <label>
          D-1 cutoff (UK)
          <input
            type="time"
            step={1800}
            value={query.cutoff}
            onChange={(e) => e.target.value && set({ cutoff: e.target.value })}
          />
        </label>
      ) : (
        <label className="slider">
          Horizon: <strong>{query.horizon}h</strong>
          <input
            type="range"
            min={0}
            max={MAX_HORIZON_H}
            step={1}
            value={query.horizon}
            onChange={(e) => set({ horizon: Number(e.target.value) })}
          />
        </label>
      )}
    </div>
  );
}
