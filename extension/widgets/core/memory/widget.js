// Memory widget: logic and data mapping. Its look is in widget.svg next to this file.
import {THEME} from '../../lib/theme.js';
import {dot} from '../../lib/svg.js';
import {card, percent} from '../../lib/format.js';

export const meta = {id: 'memory', name: 'Memory', category: 'system', kind: 'card', size: '2x1', description: 'A memory module whose gold pins light up with use', author: 'Attahiru Jibril'};

export function build(sample) {
    const m = sample.memory;
    const fraction = m ? m.used / m.total : NaN;
    return card(m ? `MEMORY · ${percent(fraction)}` : 'MEMORY', '', {chart: {fraction, sticks: 2,
        capacity: m ? `${Math.round(m.total / 2 ** 30)}G` : '—'}});
}

// One DDR module is 440 x 100 units; each later module sits down and to the right of the one before.
const W = 440, H = 100, BODY = 84, STEP_X = 50, STEP_Y = 70;

function stick(i, n, f, label) {
    const r = H * 0.05, ym = BODY * 0.5, nr = H * 0.1, pitch = Math.max(2, W / 120), fw = pitch * 0.5;
    const key = W * 0.58, kw = pitch * 2.4, kd = H * 0.1;
    // One continuous outline with the latch notches and the key notch cut into it.
    const outline = `M${r} 0H${W - r}A${r} ${r} 0 0 1 ${W} ${r}V${ym - nr}A${nr} ${nr} 0 0 0 ${W} ${ym + nr}V${H - r}`
        + `A${r} ${r} 0 0 1 ${W - r} ${H}H${key + kw / 2}V${H - kd}H${key - kw / 2}V${H}H${r}A${r} ${r} 0 0 1 0 ${H - r}`
        + `V${ym + nr}A${nr} ${nr} 0 0 0 0 ${ym - nr}V${r}A${r} ${r} 0 0 1 ${r} 0Z`;
    // Many thin gold fingers along the bottom edge, interrupted by the key notch.
    const fingers = [];
    for (let x = nr * 1.4; x + fw < W - nr * 1.4; x += pitch) {
        if (x + fw > key - kw / 2 - pitch * 0.5 && x < key + kw / 2 + pitch * 0.5) continue;
        fingers.push({x, lit: x + fw / 2 <= W * f});
    }
    // Eight memory chips; a labelled module gives the SPD chip's place to its figure.
    const gap = W * 0.012, left = W * (label ? 0.18 : 0.11), cw = (W * (label ? 0.78 : 0.85) - 7 * gap) / 8;
    const ch = BODY * 0.5, top = BODY * 0.2;
    const chips = Array.from({length: 8}, (_, k) => {
        const x = left + k * (cw + gap);
        return {x, y: top, w: cw, h: ch, dot: dot(x + cw * 0.18, top + ch * 0.16, Math.max(0.7, cw * 0.045), 'currentColor'),
            lines: [0, 1, 2].map(j => ({x1: x + cw * 0.22, x2: x + cw * 0.78, y: top + ch * (0.4 + j * 0.17)}))};
    });
    const caps = Array.from({length: 16}, (_, k) => ({x: W * (0.1 + k * 0.054)}));
    const more = i < n - 1;
    return {i, x: i * STEP_X + (more ? 4 : 0), y: i * STEP_Y + (more ? 4 : 0), outline, fingers, fw, chips, caps, spd: !label, next: more, nx: (i + 1) * STEP_X, ny: (i + 1) * STEP_Y, nx2: (i + 1) * STEP_X + W, ny2: (i + 1) * STEP_Y + H,
        label, labelSize: label ? Math.min(BODY * 0.3, W * 0.13 / (label.length * 0.6)) : 0};
}

export const chart = {
    size(c, w, h) {
        const n = c.sticks ?? 1, spanX = 4.4 + (n - 1) * 0.5, spanY = 1 + (n - 1) * 0.7;
        const unit = Math.min(w / spanX, h / spanY);
        return [Math.round(unit * spanX), Math.round(unit * spanY)];
    },
    vars(c) {
        const n = c.sticks ?? 1, f = Number.isFinite(c.fraction) ? Math.min(1, Math.max(0, c.fraction)) : 0;
        // The front module carries the usage figure; the ones behind it show the installed capacity.
        const sticks = Array.from({length: n}, (_, i) => stick(i, n, i === n - 1 ? f : 0, i === n - 1 || !c.capacity ? percent(c.fraction) : c.capacity));
        return {sticks, vw: W + (n - 1) * STEP_X, vh: H + (n - 1) * STEP_Y};
    },
};
