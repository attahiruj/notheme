// Day widget: logic and data mapping. Its look is in widget.svg next to this file.
import {THEME} from '../../lib/theme.js';
import {square} from '../../lib/charts.js';
import {dot} from '../../lib/svg.js';
import {card} from '../../lib/format.js';

export const meta = {id: 'day-progress', name: 'Day', category: 'progress', kind: 'card', size: '1x1', description: 'A clock face of twenty-four hour dots', author: 'Attahiru Jibril'};

export function build(sample) {
    const time = sample.time;
    const fraction = time ? (time.hour * 3600 + time.minute * 60 + time.second) / 86400 : NaN;
    return card('DAY', '', {chart: {fraction, hour: time ? time.hour : -1}});
}

const R = 47;

export const chart = {
    size: square(300),
    vars(c) {
        const hour = c.hour ?? -1;
        // The day as a ring of hours: night hours small, daylight hours large.
        let ring = '';
        for (let i = 0; i < 24; i++) {
            const a = -Math.PI / 2 + i / 24 * Math.PI * 2, day = i >= 6 && i < 18, r = R * (day ? 0.07 : 0.045);
            ring += dot(50 + Math.cos(a) * (R - r * 2), 50 + Math.sin(a) * (R - r * 2), i === hour ? r * 1.6 : r,
                i === hour ? THEME.accent : i < hour ? THEME.fg : THEME.line);
        }
        const rays = Array.from({length: 8}, (_, i) => {
            const a = i / 8 * Math.PI * 2, g = R * 0.26;
            return {x1: Math.cos(a) * g * 0.8, y1: Math.sin(a) * g * 0.8, x2: Math.cos(a) * g * 1.1, y2: Math.sin(a) * g * 1.1};
        });
        return {ring, day: hour >= 6 && hour < 18, rays};
    },
};
