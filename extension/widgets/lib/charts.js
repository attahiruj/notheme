// Chart registry. A widget with a drawing exports `chart` in one of two forms:
//   {size?, vars(chart, w, h)}    and ships a widget.svg template that the values fill in, or
//   {size?, render(chart, w, h, theme)}  and returns the whole SVG document itself, in plain JS.
// Use the template when the design is mostly static art; use render() when the drawing is mostly logic.
// renderChart() returns an SVG document that any toolkit can show.
import {THEME} from './theme.js';
import {renderTemplate} from './template.js';

const CHARTS = new Map();
let uid = 0;
export const registerChart = chart => CHARTS.set(chart.type, chart);

// Canvas size for a chart in a card with `width` x `height` pixels of room.
export function canvasSize(chart, width, height) {
    const w = Math.max(40, Math.round(width));
    const h = Math.max(32, Math.round(height));
    return CHARTS.get(chart.type)?.size?.(chart, w, h) ?? [w, h];
}

// The theme, as template values: {{bg}} {{fg}} {{dim}} {{muted}} {{line}} {{accent}} {{font}} {{mono}}.
// {{w}} and {{h}} are the pixel size, {{square}} the dot shape, {{uid}} a number unique to this render
// (for ids inside the SVG).
export function renderChart(chart, w, h) {
    const entry = CHARTS.get(chart.type);
    if (!entry) return '';
    const theme = {
        bg: THEME.bg, fg: THEME.fg, dim: THEME.dim, muted: THEME.muted, line: THEME.line, accent: THEME.accent,
        font: THEME.font, mono: 'Space Mono', w, h, square: THEME.square, uid: ++uid,
    };
    if (entry.render) return entry.render(chart, w, h, theme);
    if (!entry.template) return '';
    return renderTemplate(entry.template, {...theme, ...entry.vars(chart, w, h)});
}

// Common size rule: the largest square that fits, optionally capped.
export const square = (cap = Infinity) => (_chart, w, h) => { const side = Math.min(w, h, cap); return [side, side]; };
