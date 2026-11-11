// Processor widget: logic and data mapping. Its look is in widget.svg next to this file.
import {THEME} from '../../lib/theme.js';
import {square} from '../../lib/charts.js';
import {dot, clamp01} from '../../lib/svg.js';
import {card} from '../../lib/format.js';

export const meta = {id: 'cpu', name: 'Processor', category: 'system', kind: 'card', size: '1x1', description: 'Dot-matrix graph of the last minute of load', author: 'Attahiru Jibril'};

export function build(sample) {
    return card('CPU', '', {
        chart: {series: sample.history?.cpu ?? [], load: sample.cpu}, alert: sample.cpu >= 0.9});
}

// The graph is laid out in the chip body (67.2 x 56 units): COLS columns, one per recent sample.
const COLS = 11, WIDTH = 67.2, HEIGHT = 56;

export const chart = {
    size: square(),
    vars(c) {
        const step = WIDTH / COLS, rows = Math.floor(HEIGHT / step), r = Math.max(1.2, step * 0.3);
        const bottom = HEIGHT - (HEIGHT - rows * step) / 2; // centred, so top and bottom margins match
        const values = [...Array(Math.max(0, COLS - c.series.length)).fill(0), ...c.series.slice(-COLS)];
        let dots = '';
        for (let i = 0; i < COLS; i++) {
            const lit = Math.round(clamp01(values[i]) * rows);
            for (let j = 0; j < rows; j++)
                dots += dot(step / 2 + i * step, bottom - (j + 0.5) * step, r,
                    j >= lit ? THEME.line : (j === lit - 1 && i === COLS - 1) ? THEME.accent : THEME.fg);
        }
        return {dots};
    },
};
