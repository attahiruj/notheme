// Year widget: logic and data mapping. Its look is in widget.svg next to this file.
import {THEME} from '../../lib/theme.js';
import {dot} from '../../lib/svg.js';
import {card} from '../../lib/format.js';

export const meta = {id: 'year-progress', name: 'Year', category: 'progress', kind: 'card', size: '2x1', description: 'Fifty-two dots, one per week of the year', author: 'Attahiru Jibril'};

export function build(sample) {
    const time = sample.time;
    return card(time ? `YEAR ${time.year}` : 'YEAR', '', {
        chart: {year: time?.year ?? 2000, dayOfYear: time?.dayOfYear ?? 0}});
}

// Twelve rows of days in a 328 x 120 box (a step of 10 units): passed days lit, today red.
const STEP = 10, LEFT = 18;

export const chart = {
    size(_chart, w, h) {
        const step = Math.min(w / 32.8, h / 12);
        return [Math.round(step * 32.8), Math.round(step * 12)];
    },
    vars(c) {
        const leap = (c.year % 4 === 0 && c.year % 100 !== 0) || c.year % 400 === 0;
        const months = [31, leap ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
        let day = 0, days = '';
        for (let m = 0; m < 12; m++)
            for (let d = 0; d < months[m]; d++) {
                day++;
                days += dot(LEFT + (d + 0.5) * STEP, (m + 0.5) * STEP, day === c.dayOfYear ? 4 : 3,
                    day === c.dayOfYear ? THEME.accent : day < c.dayOfYear ? THEME.fg : THEME.line);
            }
        return {days, letters: [...'JFMAMJJASOND'].map((text, m) => ({text, y: (m + 0.5) * STEP}))};
    },
};
