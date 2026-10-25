import { useState } from 'react';
import { NavLink, Route, Routes } from 'react-router-dom';
import { DEFAULT_QUERY, type Query } from './api';
import { Controls } from './components/Controls';
import { AccuracyView } from './pages/AccuracyView';
import { DayAheadView } from './pages/DayAheadView';
import { useTheme } from './themeContext';

export function App() {
  const { theme, toggle } = useTheme();
  // Filters are shared across pages so switching tabs keeps context.
  const [query, setQuery] = useState<Query>(DEFAULT_QUERY);

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <strong>Wind Forecast Desk</strong>
          <span className="muted">GB national wind · Elexon BMRS · Jan 2026 decisions</span>
        </div>
        <nav>
          <NavLink to="/" end>
            Day-ahead view
          </NavLink>
          <NavLink to="/accuracy">Forecast accuracy</NavLink>
        </nav>
        <button
          type="button"
          className="theme-toggle"
          onClick={toggle}
          aria-label="Toggle colour theme"
        >
          {theme === 'light' ? 'Dark' : 'Light'} mode
        </button>
      </header>
      <main>
        <Controls query={query} onChange={setQuery} />
        <Routes>
          <Route path="/" element={<DayAheadView query={query} />} />
          <Route path="/accuracy" element={<AccuracyView query={query} />} />
        </Routes>
      </main>
    </div>
  );
}
