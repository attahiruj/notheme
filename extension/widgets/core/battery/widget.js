// Battery widget: logic and data mapping. Its look is in widget.svg next to this file.
import {THEME} from '../../lib/theme.js';
import {card} from '../../lib/format.js';

export const meta = {id: 'battery', name: 'Battery', category: 'system', kind: 'card', size: '1x1', description: 'Ten-cell battery with charge and state', author: 'Attahiru Jibril'};

export function build(sample) {
    const b = sample.battery;
    if (!b) return card('BATTERY', '', {chart: {fraction: NaN}});
    const charging = b.status.toLowerCase() === 'charging';
    const alert = b.percent <= 15 && !charging;
    return card('BATTERY', '', {alert, chart: {fraction: b.percent / 100, alert, charging}});
}

// Drawn in a 120 x 90 box: a cell with its terminal, ten segments, and the charge as a number beneath.
const W = 120, H = 90, BW = W - 8, BH = H * 0.56;

export const chart = {
    size: (_chart, w, h) => [w, Math.min(h, Math.round(w * 0.75))],
    vars(c) {
        const known = Number.isFinite(c.fraction), f = known ? Math.min(1, Math.max(0, c.fraction)) : 0;
        const inset = BH * 0.14, gap = 2.5, cw = (BW - inset * 2 - gap * 9) / 10, lit = Math.round(f * 10);
        const segments = Array.from({length: 10}, (_, i) => ({x: inset + i * (cw + gap),
            color: i >= lit ? THEME.line : (c.alert || i === lit - 1) ? THEME.accent : THEME.fg}));
        const size = Math.min((H - BH) * 0.72, W * 0.26), label = known ? `${Math.round(f * 100)}%` : '—';
        const shift = c.charging ? size * 0.4 : 0;
        let bolt = '';
        if (c.charging) {
            const bx = W / 2 + shift - size * (label.length * 0.42) - size * 0.35, u = size * 0.5, ty = BH + (H - BH) / 2;
            bolt = [[bx + u * 0.15, ty - u], [bx - u * 0.45, ty + u * 0.12], [bx - u * 0.05, ty + u * 0.12], [bx - u * 0.2, ty + u],
                [bx + u * 0.45, ty - u * 0.2], [bx + u * 0.05, ty - u * 0.2]].map(p => p.map(v => v.toFixed(2)).join(',')).join(' ');
        }
        return {segments, cw, inset, label, size, labelX: W / 2 + shift, labelY: BH + (H - BH) / 2,
            labelFill: c.alert ? THEME.accent : THEME.fg, bolt};
    },
};
