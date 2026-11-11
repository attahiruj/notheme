// Temperature widget: logic and data mapping. Its look is in widget.svg next to this file.
import {THEME} from '../../lib/theme.js';
import {card} from '../../lib/format.js';

export const meta = {id: 'temperature', name: 'Temperature', category: 'system', kind: 'card', size: '1x2', description: 'Half-circle tick gauge from hardware sensors', author: 'Attahiru Jibril'};

export function build(sample) {
    const t = sample.temperature;
    const known = Number.isFinite(t);
    return card('CPU TEMP', '', {alert: t >= 85,
        chart: {fraction: known ? (t - 30) / 70 : NaN, center: known ? `${Math.round(t)}°` : '—',
            alert: t >= 85}});
}

// A thermometer drawn in a 55 x 100 box: tube and bulb, liquid that rises with the reading, scale and number.
const W = 55, H = 100, TW = W * 0.2, CX = W * 0.26, R = W * 0.18, BY = H - R - 3, TOP = 4 + TW / 2;

export const chart = {
    size: (_chart, w, h) => [Math.min(w, Math.round(h * 0.55)), h],
    vars(c) {
        const known = Number.isFinite(c.fraction), f = known ? Math.min(1, Math.max(0, c.fraction)) : 0;
        const alarm = c.alert ? THEME.accent : THEME.fg;
        const theta = Math.asin(TW / 2 / R), level = BY - (BY - TOP) * f, tickX = CX + TW / 2 + 7;
        const outline = `M${CX - TW / 2} ${TOP}A${TW / 2} ${TW / 2} 0 0 1 ${CX + TW / 2} ${TOP}V${BY - R * Math.cos(theta)}`
            + `A${R} ${R} 0 1 1 ${CX - TW / 2} ${BY - R * Math.cos(theta)}Z`;
        const ticks = [2, 6, 10, 14].map(i => {
            const y = BY - (BY - TOP) * (i / 14);
            return {y, x1: tickX, x2: tickX + W * 0.16, color: y >= level && known ? alarm : THEME.line,
                label: i > 2 ? String(30 + i * 5) : '', labelX: tickX + W * 0.36};
        });
        return {outline, known, bulbX: CX, bulbY: BY, bulbR: R * 0.68, fill: known ? alarm : THEME.line,
            liquidX: CX - TW * 0.24, liquidY: level, liquidW: TW * 0.48, liquidH: BY - level, ticks, tickSize: W * 0.1,
            center: known ? c.center : '—', centerX: W * 0.7, centerY: BY + R * 0.62, centerSize: W * 0.25, alarm};
    },
};
