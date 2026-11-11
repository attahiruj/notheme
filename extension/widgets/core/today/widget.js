// Today widget. Self-contained: everything specific to it lives in this file.
import {card, pad} from '../../lib/format.js';

export const meta = {id: 'today', name: 'Today', category: 'time', kind: 'card', size: '3x1', description: 'Weekday, date and week number, with a greeting for the time of day', aliases: ['date', 'greeting'], author: 'Attahiru Jibril'};

export function build(sample, options) {
    const time = sample.time;
    const hour = time?.hour ?? 12;
    const name = options.name ? `, ${options.name}` : '';
    // Greeting first and large, the date line beneath it, both flush left.
    return card('', `Good ${hour < 12 ? 'morning' : hour < 18 ? 'afternoon' : 'evening'}${name}.`, {
        greeting: true, left: true,
        caption: time ? `${time.weekdayName} · ${pad(time.day)} ${time.monthName} · WEEK ${pad(time.week)}`.toUpperCase() : '—'});
}
