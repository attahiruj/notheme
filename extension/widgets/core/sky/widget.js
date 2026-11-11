// Sky widget: the sun by day, the moon's phase by night. Logic and data mapping. Its look is in widget.svg next to this file.
import {THEME} from '../../lib/theme.js';
import {square} from '../../lib/charts.js';
import {dot} from '../../lib/svg.js';
import {card} from '../../lib/format.js';

export const meta = {id: 'sky', name: 'Sky', category: 'time', kind: 'card', size: '1x1', description: 'A sun by day, tonight\'s moon phase after dark', aliases: ['moon'], author: 'Attahiru Jibril'};


const SYNODIC = 29.530588853;

// 0 = new moon, 0.5 = full. Anchored on the new moon of 2000-01-06 18:14 UTC.
export function moonPhase(year, month, day, hour = 12) {
    const days = Date.UTC(year, month - 1, day, hour) / 86400000 + 2440587.5 - 2451550.1;
    return (((days % SYNODIC) + SYNODIC) % SYNODIC) / SYNODIC;
}

export function moonName(phase) {
    const names = [[0.03, 'New'], [0.22, 'Waxing crescent'], [0.28, 'First quarter'], [0.47, 'Waxing gibbous'],
        [0.53, 'Full'], [0.72, 'Waning gibbous'], [0.78, 'Last quarter'], [0.97, 'Waning crescent']];
    return (names.find(([limit]) => phase < limit) ?? [1, 'New'])[1];
}

export function build(sample) {
    const time = sample.time;
    const phase = time ? moonPhase(time.year, time.month, time.day, time.hour) : 0.25;
    const hour = time ? time.hour : 22;
    return card('SKY', '', {chart: {phase, day: hour >= 6 && hour < 18}});
}

// Craters as [x, y, radius] fractions of the moon's radius.
const CRATERS = [[-0.3, -0.28, 0.2], [0.28, 0.12, 0.24], [0.02, 0.52, 0.12], [-0.4, 0.3, 0.1], [0.45, -0.42, 0.1],
    [0.05, -0.05, 0.08], [-0.12, 0.2, 0.06], [0.6, 0.45, 0.07]];
const R = 41;

export const chart = {
    size: square(300),
    vars(c) {
        // The lit part is real phase geometry: a half disc closed by an ellipse arc.
        const rays = Array.from({length: 16}, (_, i) => {
            const a = i / 16 * Math.PI * 2, long = i % 2 === 0, from = R * 0.66, to = R * (long ? 0.98 : 0.86);
            return {x1: Math.cos(a) * from, y1: Math.sin(a) * from, x2: Math.cos(a) * to, y2: Math.sin(a) * to, w: long ? 1.6 : 1};
        });
        const k = Math.cos(c.phase * Math.PI * 2), waxing = c.phase < 0.5;
        let ring = '';
        for (let i = 0; i < 48; i++) {
            const a = i / 48 * Math.PI * 2;
            ring += dot(50 + Math.cos(a) * (R + 6), 50 + Math.sin(a) * (R + 6), 0.8, THEME.line);
        }
        return {ring, day: Boolean(c.day), rays, sunr: R * 0.5, lit: Math.abs(k) < 0.999 || k < 0,
            shape: `M0 ${-R}A${R} ${R} 0 0 1 0 ${R}A${Math.max(0.001, Math.abs(k)) * R} ${R} 0 0 ${k >= 0 ? 0 : 1} 0 ${-R}Z`,
            flip: waxing ? 'translate(0 0)' : 'scale(-1 1)',
            craters: CRATERS.map(([x, y, r]) => ({x: x * R, y: y * R, r: r * R}))};
    },
};
