import { createContext, useContext } from 'react';

export type Theme = 'light' | 'dark';

/** Chart colours per theme (reference palette: slot 1 blue, slot 2 orange). */
export const PALETTES = {
  light: {
    forecast: '#2a78d6',
    actual: '#eb6834',
    band: '#86b6ef',
    grid: '#e4e3df',
    axis: '#52514e',
    surface: '#fcfcfb',
    text: '#0b0b0b',
  },
  dark: {
    forecast: '#3987e5',
    actual: '#d95926',
    band: '#1c5cab',
    grid: '#33332f',
    axis: '#c3c2b7',
    surface: '#1a1a19',
    text: '#f0efec',
  },
} as const;

export type ChartColors = (typeof PALETTES)[Theme];

interface ThemeCtx {
  theme: Theme;
  colors: ChartColors;
  toggle: () => void;
}

export const ThemeContext = createContext<ThemeCtx>({
  theme: 'light',
  colors: PALETTES.light,
  toggle: () => {},
});

export const useTheme = () => useContext(ThemeContext);
