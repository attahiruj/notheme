// Dot dial widget: logic and data mapping. Its look is in widget.svg next to this file.
import {THEME} from '../../lib/theme.js';
import {square} from '../../lib/charts.js';
import {dot} from '../../lib/svg.js';
import {card} from '../../lib/format.js';

export const meta = {id: 'dial', name: 'Dot dial', category: 'time', kind: 'card', size: '1x1', description: 'Round analog clock: sixty dots, two hands, a red second', author: 'Attahiru Jibril'};

export function build(sample) {
    const time = sample.time;
    return card('LOCAL', '', {
        chart: {hour: time?.hour ?? 10, minute: time?.minute ?? 10, second: time?.second ?? 30}});
}

// Hour marks between the numerals, as line ends in the 100x100 drawing.
const BARS = [
    {x1: 67.86, y1: 19.07, x2: 71.62, y2: 12.55},
    {x1: 80.93, y1: 32.14, x2: 87.45, y2: 28.38},
    {x1: 80.93, y1: 67.86, x2: 87.45, y2: 71.62},
    {x1: 67.86, y1: 80.93, x2: 71.62, y2: 87.45},
    {x1: 32.14, y1: 80.93, x2: 28.38, y2: 87.45},
    {x1: 19.07, y1: 67.86, x2: 12.55, y2: 71.62},
    {x1: 19.07, y1: 32.14, x2: 12.55, y2: 28.38},
    {x1: 32.14, y1: 19.07, x2: 28.38, y2: 12.55},
];

export const chart = {
    size: square(300),
    vars(c) {
        // Sixty minute dots: the current second red, passed seconds dim, the rest faint.
        let ticks = '';
        for (let i = 0; i < 60; i++) {
            if (i % 5 === 0) continue;
            const a = i / 60 * Math.PI * 2 - Math.PI / 2;
            ticks += dot(50 + Math.cos(a) * 40.89, 50 + Math.sin(a) * 40.89, i === c.second ? 1.41 : 0.66,
                i === c.second ? THEME.accent : i < c.second ? THEME.dim : THEME.line);
        }
        return {ticks, bars: BARS,
            hourAngle: ((c.hour % 12) + c.minute / 60) * 30, minuteAngle: c.minute * 6, secondAngle: c.second * 6};
    },
};
