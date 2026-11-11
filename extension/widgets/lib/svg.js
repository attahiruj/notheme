// Helpers for building SVG fragments in a widget's JS, to drop into its widget.svg with {{{name}}}.
import {THEME} from './theme.js';

const n = value => Math.round(value * 100) / 100;

// A dot in the user's chosen shape (round or square).
export function dot(x, y, r, color, opacity = 1) {
    const alpha = opacity < 1 ? ` fill-opacity="${opacity}"` : '';
    return THEME.square
        ? `<rect x="${n(x - r)}" y="${n(y - r)}" width="${n(r * 2)}" height="${n(r * 2)}" fill="${color}"${alpha}/>`
        : `<circle cx="${n(x)}" cy="${n(y)}" r="${n(r)}" fill="${color}"${alpha}/>`;
}

export const clamp01 = value => Number.isFinite(value) ? Math.min(1, Math.max(0, value)) : 0;

// A complete SVG document of w x h pixels around `inner` markup. Pass `box` ('0 0 100 100') to draw in
// your own units; the drawing then scales to the pixel size.
export const svgDocument = (w, h, inner, box = `0 0 ${w} ${h}`) =>
    `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="${box}">${inner}</svg>`;
