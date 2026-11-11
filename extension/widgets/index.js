// Widget registry and public API.
//
// Widgets come in two groups, each in its own folder:
//   core/  the widgets that ship with notheme (maintained by the main developers)
//   user/  widgets you create; `./notheme widget new <id>` scaffolds one and registers it
// A widget is a folder: widget.js (meta, build(sample, options) and, for a drawing, `chart`) and
// widget.svg (the drawing, a template filled with the chart's values). Shared helpers live in lib/.
//
// sample (from sampler.js) -> buildView(id) -> view -> mountWidget(adapter) -> actors
// A view is plain data; adapters turn it into St actors or Gtk widgets.
import * as clock from './core/clock/widget.js';
import * as today from './core/today/widget.js';
import * as dial from './core/dial/widget.js';
import * as sky from './core/sky/widget.js';
import * as calendar from './core/calendar/widget.js';
import * as cpu from './core/cpu/widget.js';
import * as cores from './core/cores/widget.js';
import * as memory from './core/memory/widget.js';
import * as disk from './core/disk/widget.js';
import * as battery from './core/battery/widget.js';
import * as temperature from './core/temperature/widget.js';
import * as uptime from './core/uptime/widget.js';
import * as dayProgress from './core/day-progress/widget.js';
import * as yearProgress from './core/year-progress/widget.js';
import {USER_WIDGETS} from './user/index.js';
import {registerChart} from './lib/charts.js';

export {THEME, setTheme, spanSize} from './lib/theme.js';
export {SHAPES, fitRows, fitColumns, packCards, dropCard} from './lib/layout.js';
export {canvasSize} from './lib/charts.js';
export {mountWidget} from './lib/mount.js';
export {renderChart} from './lib/charts.js';
export {renderTemplate} from './lib/template.js';
export {formatBytes, formatDuration, meter} from './lib/format.js';
export {clockText} from './core/clock/widget.js';
export {calendarCells} from './core/calendar/widget.js';
export {moonPhase, moonName} from './core/sky/widget.js';
export {uptimeParts} from './core/uptime/widget.js';

export const CATEGORIES = [
    ['all', 'All'], ['time', 'Time'], ['system', 'System'], ['progress', 'Progress'],
];
// Where a widget comes from, in display order.
export const ORIGINS = [['core', 'Built-in'], ['user', 'Yours']];

// Every widget, text or card, occupies a fixed shape on the same grid of units, so any of them can
// sit beside another. meta.size: columns x rows of grid units each widget is designed for.
const CORE_WIDGETS = [clock, today, dial, sky, calendar, cpu, cores, memory, disk, battery, temperature, uptime, dayProgress, yearProgress];
// Core widgets are trusted. A user widget is rejected, with a warning, when its id is malformed, taken by
// a built-in or another user widget, or is an alias an older saved layout may still use.
export function acceptWidgets(core, user) {
    const accepted = core.map(module => ({...module, origin: 'core'}));
    const taken = new Set(core.flatMap(({meta}) => [meta.id, ...(meta.aliases ?? [])]));
    const rejected = [];
    for (const module of user) {
        const id = module?.meta?.id;
        const reason = typeof id !== 'string' || !/^[a-z][a-z0-9-]{0,30}$/.test(id) ? 'id must be lowercase letters, digits and dashes'
            : taken.has(id) ? 'id is already used by another widget or an alias'
            : typeof module.build !== 'function' ? 'missing build()' : '';
        if (reason) { rejected.push({id: String(id), reason}); continue; }
        taken.add(id);
        for (const alias of module.meta.aliases ?? []) taken.add(alias);
        accepted.push({...module, origin: 'user'});
    }
    return {accepted, rejected};
}

const {accepted: WIDGETS, rejected: REJECTED} = acceptWidgets(CORE_WIDGETS, USER_WIDGETS);
for (const {id, reason} of REJECTED) console.warn(`notheme: widget "${id}" ignored: ${reason}`);
export const REJECTED_WIDGETS = REJECTED;

// Where each templated widget's drawing lives, relative to this folder (widgets that render in JS have none).
export const templatePaths = () => WIDGETS.filter(widget => widget.chart && !widget.chart.render).map(widget => `${widget.origin}/${widget.meta.id}/widget.svg`);

// Pair every widget's chart with its widget.svg. `read(path)` returns the file's text synchronously
// (GLib in the Shell, a prefetched map in preferences, fs in Node). Call once before mounting.
export function loadTemplates(read) {
    for (const widget of WIDGETS) {
        if (!widget.chart) continue;
        const template = widget.chart.render ? null : read(`${widget.origin}/${widget.meta.id}/widget.svg`);
        registerChart({...widget.chart, type: widget.meta.id, template});
    }
}

export const CATALOG = WIDGETS.map(widget => ({...widget.meta, origin: widget.origin}));

const BY_ID = new Map(WIDGETS.map(widget => [widget.meta.id, widget]));
export const DEFAULT_WIDGETS = ['clock', 'today', 'cpu', 'memory'];
// Widgets that replaced older ones: saved lists and cells may still name the old ids.
const ALIASES = Object.fromEntries(WIDGETS.flatMap(({meta}) => (meta.aliases ?? []).map(alias => [alias, meta.id])));
const canon = id => ALIASES[id] ?? id;
const LEGACY_KEYS = ['show-clock', 'show-date', 'show-greeting', 'show-stats', 'show-cpu', 'show-memory'];

export const widgetInfo = id => CATALOG.find(info => info.id === id) ?? null;

// A card's shape is part of its design and cannot be changed.
export const sizeOf = id => BY_ID.get(id)?.meta.size ?? '1x1';

// The widget-cells setting holds "id@col,row" entries (0-based). Returns Map id -> {col, row}.
export function parseCells(list) {
    const map = new Map();
    for (const entry of list ?? []) {
        const m = /^([a-z0-9-]+)@(\d{1,2}),(\d{1,2})$/.exec(entry);
        const id = m && canon(m[1]);
        if (m && BY_ID.has(id) && !map.has(id)) map.set(id, {col: Number(m[2]), row: Number(m[3])});
    }
    return map;
}

// Pin `id` to a grid cell, or release it to automatic placement when `at` is null.
export function setCell(list, id, at) {
    const map = parseCells(list);
    if (at) map.set(id, at);
    else map.delete(id);
    return [...map].map(([key, v]) => `${key}@${v.col},${v.row}`);
}

// Unknown ids (from a newer or older version) and duplicates are dropped.
export function normalizeWidgets(list) {
    const seen = new Set();
    return (list ?? []).map(canon).filter(id => BY_ID.has(id) && !seen.has(id) && seen.add(id));
}

export function toggleWidget(list, id) {
    const current = normalizeWidgets(list);
    if (!BY_ID.has(id)) return current;
    return current.includes(id) ? current.filter(item => item !== id) : [...current, id];
}

export function moveWidget(list, id, delta) {
    const current = normalizeWidgets(list);
    const from = current.indexOf(id);
    const to = from + delta;
    if (from < 0 || to < 0 || to >= current.length) return current;
    current.splice(from, 1);
    current.splice(to, 0, id);
    return current;
}

// Older versions stored one boolean per widget. Carry customized choices over
// once; untouched defaults already match DEFAULT_WIDGETS.
export function migrateLegacyWidgets(settings) {
    if (settings.get_user_value('widgets') !== null) return false;
    if (!LEGACY_KEYS.some(key => settings.get_user_value(key) !== null)) return false;
    const on = key => settings.get_boolean(key);
    const stats = on('show-stats');
    const list = [['clock', on('show-clock')], ['today', on('show-date') || on('show-greeting')],
        ['cpu', stats && on('show-cpu')], ['memory', stats && on('show-memory')]]
        .filter(([, enabled]) => enabled).map(([id]) => id);
    settings.set_strv('widgets', list);
    return true;
}

export function buildView(id, sample = {}, options = {}) {
    const widget = BY_ID.get(id);
    const view = widget ? widget.build(sample, options) : {kind: 'card', title: id.toUpperCase(), value: '—', caption: ''};
    view.size = sizeOf(id);
    if (view.chart) view.chart.type = id;
    // A well-drawn card explains itself; titles only stay when the drawing cannot say it
    // (which city, which month) or when the user asks for them.
    if (view.kind === 'card' && !options.titles && !widget?.meta.keepTitle) view.title = '';
    return view;
}
