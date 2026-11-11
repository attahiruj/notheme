// Cores widget: logic and data mapping. Its look is in widget.svg next to this file.
import {THEME} from '../../lib/theme.js';
import {square} from '../../lib/charts.js';
import {dot, clamp01} from '../../lib/svg.js';
import {card} from '../../lib/format.js';

export const meta = {id: 'cores', name: 'Cores', category: 'system', kind: 'card', size: '1x1', description: 'One live column per processor thread', author: 'Attahiru Jibril'};

export function build(sample) {
    const cores = sample.cores ?? [];
    const average = cores.length ? cores.reduce((sum, v) => sum + v, 0) / cores.length : NaN;
    return card('CORES', '', {
        chart: {series: cores, load: average}});
}

// One tile per thread, tiled into the chip body (67.2 x 56 units); each tile is a 5 x 3 meter.
const WIDTH = 67.2, HEIGHT = 56;

export const chart = {
    size: square(),
    vars(c) {
        const n = c.series.length;
        if (!n) return {tiles: []};
        const gap = WIDTH * 0.03, cols = Math.ceil(Math.sqrt(n * WIDTH / HEIGHT)), rows = Math.ceil(n / cols);
        const tw = (WIDTH - (cols - 1) * gap) / cols, th = (HEIGHT - (rows - 1) * gap) / rows;
        const mr = 5, mc = 3, step = Math.min(tw / (mc + 0.8), th / (mr + 0.8)), r = Math.max(0.7, step * 0.3);
        const tiles = c.series.map((load, i) => {
            const x = (i % cols) * (tw + gap), y = Math.floor(i / cols) * (th + gap);
            const lit = Math.round(clamp01(load) * mr);
            let dots = '';
            for (let j = 0; j < mr; j++)
                for (let k = 0; k < mc; k++)
                    dots += dot(x + tw / 2 + (k - (mc - 1) / 2) * step, y + th - (th - mr * step) / 2 - (j + 0.5) * step, r,
                        j >= lit ? THEME.line : j === lit - 1 && load > 0.9 ? THEME.accent : THEME.fg);
            return {x, y, w: tw, h: th, dots};
        });
        return {tiles};
    },
};
