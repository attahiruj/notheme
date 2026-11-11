// Turns a view (plain data) into toolkit widgets through an adapter.
import {THEME, spanSize} from './theme.js';
import {SHAPES} from './layout.js';
import {canvasSize, renderChart} from './charts.js';

// Approximate line heights of a card's text, used to leave the chart the rest of the card.
const LINE = {title: 16, value: 48, compact: 30, caption: 14, gap: 12};


// ---- Mounting --------------------------------------------------------------

// Structure changes (a six-week month, a missing caption) rebuild a widget's
// children; anything else only updates text and classes in place.
const shapeOf = view => view.kind !== 'card' ? view.kind : JSON.stringify([
    Boolean(view.title), Boolean(view.caption), view.value !== '', view.size, view.chart?.type ?? '', view.left ? 1 : 0, view.chart?.columns ?? 0,
    view.chart?.mirror ? 1 : 0, view.chart?.fit ? view.chart.series.length : 0, view.meter?.total ?? 0, view.grid?.total ?? 0,
    view.grid?.columns ?? 0, view.calendar?.cells.length ?? 0,
]);

const pipClass = (index, dots) => 'notheme-pip' +
    (index === dots.current ? ' accent' : index < dots.filled ? ' on' : '');
const dayClass = cell => 'notheme-cal-day' + (cell.state ? ` ${cell.state}` : '');

const TEXT_CLASS = {clock: 'notheme-desktop-clock'};

// adapter: {box(vertical, cls), label(text, cls), dot(cls), setText, setClass, append, clear, middle?(actor),
//           size?(widget, width, height), image?(width, height, render() -> SVG document), redraw?(image)}
export function mountWidget(adapter, view) {
    if (view.kind !== 'card') {
        // Text sits centered in its cell, like the content of a card.
        const root = adapter.box(false, 'notheme-text');
        const label = adapter.label(view.text, TEXT_CLASS[view.kind]);
        adapter.middle?.(label);
        adapter.append(root, label);
        const [cols, rows] = SHAPES[view.size] ?? SHAPES['1x1'];
        adapter.size?.(root, spanSize(cols), spanSize(rows));
        return {root, update: next => adapter.setText(label, next.text)};
    }
    const root = adapter.box(true, 'notheme-card');
    let parts = null;
    let shape = null;
    let current = view;
    const build = next => {
        adapter.clear(root);
        const [cols, rows] = SHAPES[next.size] ?? SHAPES['1x1'];
        adapter.size?.(root, spanSize(cols), spanSize(rows));
        parts = {title: null, pips: [], days: [], image: null};
        // Content sits centered in the card: equal expanding spacers above and below.
        const put = child => { (next.left ? adapter.start : adapter.center)?.(child); adapter.append(root, child); };
        const spacer = () => { const gap = adapter.spacer?.(); if (gap) adapter.append(root, gap); };
        spacer();
        if (next.title) {
            parts.title = adapter.label('', 'notheme-card-title');
            put(parts.title);
        }
        if (next.value !== '') {
            parts.value = adapter.label('', 'notheme-card-value');
            put(parts.value);
        }
        if (next.chart && adapter.image) {
            const edge = 2 * (THEME.pad + THEME.border);
            // Title, optional value and caption share the card with the chart; the rest is its room.
            const used = (next.title ? LINE.title : 0) + (next.value !== '' ? (next.compact ? LINE.compact : LINE.value) : 0)
                + (next.caption ? LINE.caption : 0);
            const count = (next.title ? 1 : 0) + (next.value !== '' ? 1 : 0) + 1 + (next.caption ? 1 : 0);
            const [cw, ch] = canvasSize(next.chart, spanSize(cols) - edge,
                spanSize(rows) - edge - used - LINE.gap * (count - 1));
            parts.image = adapter.image(cw, ch, () => renderChart(current.chart, cw, ch));
            put(parts.image);
            if (!next.left) adapter.middle?.(parts.image); // centered on both axes in the card
        }
        if (next.caption) {
            parts.caption = adapter.label('', `notheme-card-caption${next.greeting ? ' greeting' : ''}`);
            put(parts.caption);
        }
        const dots = next.meter ?? next.grid;
        if (dots) {
            const columns = next.grid?.columns ?? dots.total;
            const holder = adapter.box(true, 'notheme-grid');
            let row = null;
            for (let i = 0; i < dots.total; i++) {
                if (i % columns === 0) {
                    row = adapter.box(false, 'notheme-meter');
                    adapter.append(holder, row);
                }
                const pip = adapter.dot('notheme-pip');
                parts.pips.push(pip);
                adapter.append(row, pip);
            }
            put(holder);
        }
        if (next.calendar) {
            const grid = adapter.box(true, 'notheme-calendar');
            const head = adapter.box(false, 'notheme-cal-row');
            for (const day of next.calendar.weekdays) adapter.append(head, adapter.label(day, 'notheme-cal-head'));
            adapter.append(grid, head);
            let row = null;
            next.calendar.cells.forEach((cell, i) => {
                if (i % 7 === 0) {
                    row = adapter.box(false, 'notheme-cal-row');
                    adapter.append(grid, row);
                }
                const label = adapter.label('', 'notheme-cal-day');
                parts.days.push(label);
                adapter.append(row, label);
            });
            put(grid);
        }
        spacer();
        shape = shapeOf(next);
    };
    const update = next => {
        current = next;
        if (shapeOf(next) !== shape) build(next);
        const big = next.size === '2x2' && !next.chart && !next.calendar;
        adapter.setClass(root, `notheme-card notheme-card-${next.calendar ? 'calendar' : 'stat'}` +
            `${next.alert ? ' alert' : ''}${big ? ' big' : ''}`);
        if (parts.title) adapter.setText(parts.title, next.title);
        if (parts.value) {
            adapter.setText(parts.value, next.value);
            adapter.setClass(parts.value, `notheme-card-value${next.compact ? ' compact' : ''}${next.greeting ? ' greeting' : ''}`);
        }
        if (parts.caption) adapter.setText(parts.caption, next.caption);
        if (parts.image) adapter.redraw?.(parts.image);
        const dots = next.meter ?? next.grid;
        parts.pips.forEach((pip, i) => adapter.setClass(pip, pipClass(i, dots)));
        parts.days.forEach((label, i) => {
            const cell = next.calendar.cells[i];
            adapter.setText(label, cell.text);
            adapter.setClass(label, dayClass(cell));
        });
    };
    update(view);
    return {root, update};
}
