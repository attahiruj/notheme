// Month widget. Self-contained: everything specific to it lives in this file.
import {card} from '../../lib/format.js';

export const meta = {id: 'calendar', name: 'Month', category: 'time', kind: 'card', size: '1x1', description: 'This month as a grid, today in the accent color', keepTitle: true, author: 'Attahiru Jibril'};

export function calendarCells(time) {
    const cells = [];
    for (let i = 1; i < time.firstWeekday; i++) cells.push({text: '', state: 'blank'});
    for (let day = 1; day <= time.daysInMonth; day++)
        cells.push({text: String(day), state: day === time.day ? 'today' : day < time.day ? 'past' : ''});
    while (cells.length % 7) cells.push({text: '', state: 'blank'});
    return cells;
}

export function build(sample) {
    const time = sample.time;
    return card(time ? `${time.monthName} ${time.year}`.toUpperCase() : 'MONTH', '', {
        calendar: {weekdays: ['M', 'T', 'W', 'T', 'F', 'S', 'S'], cells: time ? calendarCells(time) : []},
    });
}
