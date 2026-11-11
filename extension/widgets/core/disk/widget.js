// Storage widget: logic and data mapping. Its look is in widget.svg next to this file.
import {THEME} from '../../lib/theme.js';
import {square} from '../../lib/charts.js';
import {clamp01} from '../../lib/svg.js';
import {card, percent} from '../../lib/format.js';

export const meta = {id: 'disk', name: 'Storage', category: 'system', kind: 'card', size: '1x1', description: 'A floppy disk whose label fills with used space', author: 'Attahiru Jibril'};

export function build(sample) {
    const d = sample.disk;
    const fraction = d ? d.used / d.total : NaN;
    return card(d ? `STORAGE · ${percent(fraction)}` : 'STORAGE', '', {chart: {fraction, label: d ? percent(fraction) : '—'}});
}

export const chart = {
    size: square(),
    vars(c) {
        const f = Number.isFinite(c.fraction) ? clamp01(c.fraction) : 0;
        // Label: the figure above a row of 16 cells that fill left to right with use.
        const n = 16, gap = 1.2, cw = (76 - 4 * 2 - (n - 1) * gap) / n, lit = Math.ceil(f * n);
        const cells = Array.from({length: n}, (_, i) => ({x: 16 + i * (cw + gap),
            color: i === lit - 1 ? THEME.accent : i < lit ? THEME.fg : THEME.line}));
        return {cells, cw, label: c.label ?? '', labelSize: c.label ? Math.min(16.8, 76 * 0.9 / (c.label.length * 0.6)) : 0};
    },
};
