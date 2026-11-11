// Uptime widget: logic and data mapping. Its look is in widget.svg next to this file.
import {card, pad} from '../../lib/format.js';

export const meta = {id: 'uptime', name: 'Uptime', category: 'system', kind: 'card', size: '1x1', description: 'Time since the computer started', author: 'Attahiru Jibril'};


// The two most significant units, for split-flap tiles: days+hours, else hours+minutes.
export function uptimeParts(seconds) {
    if (!Number.isFinite(seconds) || seconds < 0) return [['--', 'H'], ['--', 'M']];
    const days = Math.floor(seconds / 86400), hours = Math.floor(seconds % 86400 / 3600);
    const minutes = Math.floor(seconds % 3600 / 60);
    return days ? [[pad(days), 'D'], [pad(hours), 'H']] : [[pad(hours), 'H'], [pad(minutes), 'M']];
}

export function build(sample) {
    return card('UPTIME', '', {chart: {parts: uptimeParts(sample.uptime)}});
}

// Split-flap tiles in a 100 x 62 box: hinge, split line and a unit under each tile.
const W = 100, H = 62, TH = H * 0.78, GAP = W * 0.06;

export const chart = {
    size: (_chart, w, h) => [w, Math.min(h, Math.round(w * 0.62))],
    vars(c) {
        const n = c.parts.length, tw = (W - GAP * (n - 1)) / n;
        return {tw, th: TH, rx: TH * 0.1, mid: TH / 2, digitY: TH / 2 + TH * 0.02, digitSize: TH * 0.52, unitY: TH + (H - TH) / 2,
            unitSize: H * 0.15, cx: tw / 2, hingeX: tw - 1, hingeR: Math.max(1.2, TH * 0.035), inner: tw - 1, innerH: TH - 1,
            tiles: c.parts.map(([text, unit], i) => ({x: i * (tw + GAP), text, unit}))};
    },
};
