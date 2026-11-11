// Colors and metrics shared by every widget. The shell and preferences each call setTheme().
// Colors and metrics for drawn charts. The shell and preferences each set these.
// bg: card surface, fg: main ink, dim: secondary ink, muted: faint ink, line: outlines and unlit marks.
export const THEME = {bg: '#000000', fg: '#F2F2F2', dim: '#8C8C8C', muted: '#4A4A4A', line: '#2A2A2A', accent: '#D71921', font: 'Doto',
    unit: 150, gap: 20, pad: 22, border: 1, square: false};
export const setTheme = values => Object.assign(THEME, values);
export const spanSize = span => span * THEME.unit + (span - 1) * THEME.gap;
