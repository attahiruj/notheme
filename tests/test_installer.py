import json
import os
from pathlib import Path
import sys
import subprocess
import tempfile
import shutil
import unittest
from unittest.mock import patch

# Never write the real user's dconf, files or desktop from tests.
os.environ['GSETTINGS_BACKEND'] = 'memory'
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import notheme


class TransactionTests(unittest.TestCase):
    def test_legacy_backups_remain_restorable_without_moving_records(self):
        import argparse
        state = self.root / 'state/notheme'
        old_state = state.parent / notheme.legacy.NAMESPACE
        old = notheme.Transaction(old_state)
        self.target.write_text('before rename')
        old.install(self.source, self.target)
        with patch.object(notheme, 'paths', return_value={'state': state}):
            self.assertIn(old.directory / 'manifest.json', notheme.backup_manifests())
            notheme.restore(argparse.Namespace(backup=old.directory.name, force=False))
        self.assertEqual(self.target.read_text(), 'before rename')
        self.assertTrue(old.directory.exists())
        self.assertFalse(state.exists())

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='notheme-test-')
        self.root = Path(self.tmp.name)
        self.tx = notheme.Transaction(self.root / 'state')
        self.source = self.root / 'source'
        self.source.write_text('notheme')
        self.target = self.root / 'target'
        notheme.settings('org.gnome.desktop.interface').reset('font-name')

    def tearDown(self):
        self.tmp.cleanup()

    def test_existing_file_round_trip(self):
        self.target.write_text('original')
        self.tx.install(self.source, self.target)
        self.assertEqual(self.target.read_text(), 'notheme')
        self.assertTrue(notheme.restore_transaction(self.tx.directory))
        self.assertEqual(self.target.read_text(), 'original')

    def test_new_file_removed_on_restore(self):
        self.tx.install(self.source, self.target)
        notheme.restore_transaction(self.tx.directory)
        self.assertFalse(self.target.exists())

    def test_symlink_backed_up_without_modifying_referent(self):
        original = self.root / 'original'
        original.write_text('untouched')
        self.target.symlink_to(original)
        self.tx.install(self.source, self.target)
        notheme.restore_transaction(self.tx.directory)
        self.assertTrue(self.target.is_symlink())
        self.assertEqual(original.read_text(), 'untouched')

    def test_broken_symlink_round_trip(self):
        self.target.symlink_to('missing')
        self.tx.install(self.source, self.target)
        notheme.restore_transaction(self.tx.directory)
        self.assertEqual(os.readlink(self.target), 'missing')

    def test_changed_files_preserved_until_force(self):
        self.target.write_text('original')
        self.tx.install(self.source, self.target)
        self.target.write_text('later user work')
        self.assertFalse(notheme.restore_transaction(self.tx.directory))
        self.assertEqual(self.target.read_text(), 'later user work')
        self.assertTrue(notheme.restore_transaction(self.tx.directory, force=True))
        self.assertEqual(self.target.read_text(), 'original')

    def test_directory_round_trip(self):
        self.source.unlink()
        self.source.mkdir()
        (self.source / 'new').write_text('new')
        self.target.mkdir()
        (self.target / 'old').write_text('old')
        self.tx.install(self.source, self.target)
        notheme.restore_transaction(self.tx.directory)
        self.assertEqual([p.name for p in self.target.iterdir()], ['old'])

    def test_settings_restore_default_not_just_effective_value(self):
        obj = notheme.settings('org.gnome.desktop.interface')
        self.assertIsNone(obj.get_user_value('font-name'))
        self.tx.set('org.gnome.desktop.interface', 'font-name', 'Space Grotesk 11')
        self.assertEqual(obj.get_string('font-name'), 'Space Grotesk 11')
        notheme.restore_transaction(self.tx.directory)
        self.assertIsNone(obj.get_user_value('font-name'))

    def test_changed_settings_preserved(self):
        obj = notheme.settings('org.gnome.desktop.interface')
        self.tx.set('org.gnome.desktop.interface', 'font-name', 'Space Grotesk 11')
        obj.set_string('font-name', 'User Later 13')
        self.assertFalse(notheme.restore_transaction(self.tx.directory))
        self.assertEqual(obj.get_string('font-name'), 'User Later 13')

    def test_identical_install_is_noop(self):
        self.target.write_text('notheme')
        self.tx.install(self.source, self.target)
        self.assertEqual(self.tx.manifest['files'], [])

    def test_manifest_exists_before_write(self):
        self.tx.install(self.source, self.target)
        m = json.loads((self.tx.directory / 'manifest.json').read_text())
        self.assertEqual(m['files'][0]['after'], notheme.digest(self.target))

    def test_nested_applies_restore_newest_first(self):
        self.target.write_text('before')
        self.tx.install(self.source, self.target)
        newer = notheme.Transaction(self.root / 'state')
        self.source.write_text('second')
        newer.install(self.source, self.target)
        notheme.restore_transaction(newer.directory)
        self.assertEqual(self.target.read_text(), 'notheme')
        notheme.restore_transaction(self.tx.directory)
        self.assertEqual(self.target.read_text(), 'before')


class BuildTests(unittest.TestCase):
    def test_desktop_layer_survives_wallpaper_replacement_and_hides_in_overview(self):
        script = '''
import fs from 'node:fs';
import assert from 'node:assert/strict';
const source = fs.readFileSync('extension/desktop-layer.js', 'utf8');
const {placeDesktop, desktopVisible} = await import('data:text/javascript;base64,' + Buffer.from(source).toString('base64'));
class Actor {
    children = []; parent = null;
    get_parent() { return this.parent; }
    add_child(child) { assert.equal(child.parent, null); this.children.push(child); child.parent = this; }
    remove_child(child) { this.children.splice(this.children.indexOf(child), 1); child.parent = null; }
    set_child_above_sibling(child, sibling) {
        assert.equal(child.parent, this); assert.equal(sibling.parent, this);
        this.remove_child(child);
        this.children.splice(this.children.indexOf(sibling) + 1, 0, child); child.parent = this;
    }
}
const windows = new Actor(), backgrounds = new Actor(), desktopIcons = new Actor(), app = new Actor(), widgets = new Actor();
windows.add_child(backgrounds); windows.add_child(desktopIcons); windows.add_child(app);
placeDesktop(widgets, windows, backgrounds);
assert.deepEqual(windows.children, [backgrounds, widgets, desktopIcons, app]);
backgrounds.add_child(new Actor()); // A wallpaper crossfade must not cover widgets.
assert.equal(widgets.parent, windows);
assert.deepEqual(windows.children, [backgrounds, widgets, desktopIcons, app]);
windows.remove_child(widgets); backgrounds.add_child(widgets); // Repair legacy placement.
placeDesktop(widgets, windows, backgrounds);
assert.deepEqual(windows.children, [backgrounds, widgets, desktopIcons, app]);
placeDesktop(widgets, windows, backgrounds); // Restacking is idempotent.
assert.equal(windows.children.filter(child => child === widgets).length, 1);
assert.equal(desktopVisible(false, false), true);
assert.equal(desktopVisible(true, false), false);
assert.equal(desktopVisible(false, true), false);
assert.equal(desktopVisible(true, true), false);
'''
        result = subprocess.run(['node', '--input-type=module', '-e', script],
                                cwd=notheme.ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        js = (notheme.ROOT / 'extension/extension.js').read_text()
        self.assertNotIn('_backgroundGroup.add_child(this._desktop)', js)
        self.assertIn("Main.overview, 'showing'", js)
        self.assertIn("Main.overview, 'hidden'", js)
        self.assertIn("global.display, 'restacked'", js)

    def test_widget_catalog_views_and_list_editing(self):
        script = r"""
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {CATALOG, DEFAULT_WIDGETS, acceptWidgets, loadTemplates, templatePaths, renderChart, buildView, calendarCells, clockText, formatBytes, formatDuration,
    meter, migrateLegacyWidgets, moonName, moonPhase, mountWidget, moveWidget, normalizeWidgets, sizeOf, canvasSize, packCards, uptimeParts,
    toggleWidget} from './extension/widgets/index.js';
assert.equal(new Set(CATALOG.map(w => w.id)).size, CATALOG.length);
for (const w of CATALOG.filter(w => w.origin === 'core')) assert.equal(w.author, 'Attahiru Jibril', w.id);
loadTemplates(path => readFileSync(`./extension/widgets/${path}`, 'utf8'));
assert.ok(templatePaths().length >= 11);
assert.deepEqual(normalizeWidgets(['cpu', 'bogus', 'cpu', 'clock']), ['cpu', 'clock']);
assert.deepEqual(toggleWidget(['clock'], 'disk'), ['clock', 'disk']);
assert.deepEqual(toggleWidget(['clock', 'disk'], 'clock'), ['disk']);
assert.deepEqual(toggleWidget(['clock'], 'bogus'), ['clock']);
assert.deepEqual(moveWidget(['a', 'clock', 'cpu'], 'cpu', -1), ['cpu', 'clock']);
assert.deepEqual(moveWidget(['clock', 'cpu'], 'clock', -1), ['clock', 'cpu']);
assert.equal(clockText(0, 5, 9, true, true), '12:05:09 AM');
assert.equal(clockText(13, 5, 9), '13:05');
assert.equal(formatBytes(5.5 * 1024 ** 3), '5.5 GB');
assert.equal(formatBytes(512 * 1024 ** 3), '512 GB');
assert.equal(formatDuration(90061), '1D 01H');
assert.deepEqual(meter(0.42), {total: 10, filled: 4, current: 3});
assert.deepEqual(meter(NaN), {total: 10, filled: 0, current: -1});
// November 2026 starts on a Sunday and has 30 days.
const time = {hour: 14, minute: 30, second: 0, year: 2026, month: 11, day: 7, week: 45, dayOfYear: 311,
    daysInYear: 365, daysInMonth: 30, firstWeekday: 7, weekdayName: 'Saturday', monthName: 'November'};
const cells = calendarCells(time);
assert.equal(cells.length % 7, 0);
assert.equal(cells.findIndex(c => c.text === '1'), 6);
assert.equal(cells.find(c => c.state === 'today').text, '7');
assert.equal(buildView('today', {time}).caption, 'SATURDAY · 07 NOVEMBER · WEEK 45');
assert.ok(Number.isNaN(buildView('battery', {}).chart.fraction));
assert.equal(buildView('today', {time}, {name: 'Ada'}).value, 'Good afternoon, Ada.');
assert.equal(buildView('today', {time}).value, 'Good afternoon.');
{
    const mod = id => ({meta: {id}, build: () => ({})});
    const coreSet = [mod('clock'), {meta: {id: 'today', aliases: ['date']}, build() {}}];
    const {accepted, rejected} = acceptWidgets(coreSet, [mod('clock'), mod('date'), mod('mine'), mod('mine'), mod('Bad Id'), {meta: {id: 'nobuild'}}]);
    assert.deepEqual(accepted.map(w => [w.meta.id, w.origin]), [['clock', 'core'], ['today', 'core'], ['mine', 'user']]);
    assert.deepEqual(rejected.map(r => r.id), ['clock', 'date', 'mine', 'Bad Id', 'nobuild']);
}
assert.equal(buildView('battery', {battery: {percent: 9, status: 'Discharging'}}).alert, true);
assert.equal(buildView('day-progress', {time}).chart.hour, time.hour);
assert.deepEqual(uptimeParts(90061), [['01', 'D'], ['01', 'H']]);
assert.deepEqual(uptimeParts(5000), [['01', 'H'], ['23', 'M']]);
assert.equal(buildView('memory', {memory: {used: 1, total: 4}}).title, '');
assert.equal(buildView('memory', {memory: {used: 1, total: 4}}, {titles: true}).title, 'MEMORY · 25%');
assert.equal(buildView('calendar', {}).title, 'MONTH');
assert.equal(buildView('memory', {memory: {used: 1, total: 4}}).chart.type, 'memory');
assert.equal(buildView('disk', {disk: {used: 1, total: 4}}).chart.type, 'disk');
assert.equal(sizeOf('calendar'), '1x1');
assert.equal(sizeOf('battery'), '1x1');
assert.equal(sizeOf('temperature'), '1x2');
assert.equal(sizeOf('cpu', {cpu: '2x2'}), '1x1', 'a card shape is fixed');
for (const w of CATALOG.filter(w => w.kind === 'card')) assert.ok(['1x1', '1x2', '2x1', '2x2', '3x1'].includes(w.size), w.id);
assert.deepEqual(packCards(['2x2', '1x1', '1x2', '1x1'], 4).cells.map(c => [c.col, c.row]), [[0, 0], [2, 0], [3, 0], [2, 1]]);
assert.equal(packCards(['2x2', '2x2'], 2).rows, 4);
assert.equal(buildView('year-progress', {time}).chart.type, 'year-progress');
assert.equal(buildView('cpu', {}).size, '1x1');
// Moon phase: the 2000-01-06 new moon, and a full moon about two weeks later.
assert.ok(moonPhase(2000, 1, 6, 19) < 0.01);
assert.ok(Math.abs(moonPhase(2000, 1, 21, 5) - 0.5) < 0.03);
assert.equal(moonName(0.5), 'Full');
assert.equal(canvasSize({type: 'sky'}, 616, 616)[1], 300);
for (const {id} of CATALOG) { buildView(id); buildView(id, {time}); }
// One renderer, any toolkit: verify in-place updates and shape rebuilds.
let created = 0;
const node = cls => ({cls, text: '', children: []});
const adapter = {box: (v, cls) => (created++, node(cls)), label: (text, cls) => (created++, {...node(cls), text}),
    dot: cls => (created++, node(cls)), setText: (l, t) => { l.text = t; }, setClass: (a, c) => { a.cls = c; },
    append: (p, c) => p.children.push(c), clear: p => { p.children = []; }};
const cpu = mountWidget(adapter, buildView('cpu', {cpu: 0.1}, {titles: true}));
const before = created;
cpu.update(buildView('cpu', {cpu: 0.55}, {titles: true}));
assert.equal(created, before);
assert.equal(cpu.root.children.length, 1, 'title only: no value text, the drawing carries the load');
// Charts draw through a canvas and repaint in place with every update.
let paints = 0, drawn = 0;
const chartAdapter = {...adapter, size: () => {}, image: (w, h, render) => ({w, h, render, children: []}),
    redraw: c => { paints++; }};
const graph = mountWidget(chartAdapter, buildView('cpu', {cpu: 0.2, history: {cpu: [0.1, 0.9]}}, {titles: true}));
const canvas = graph.root.children[1];
assert.ok(canvas.w > 50 && canvas.h > 20);
// Every drawing renders to a well-formed SVG document at the theme colors.
const docs = {};
for (const id of ['cpu', 'cores', 'memory', 'disk', 'battery', 'temperature', 'dial', 'sky', 'day-progress', 'year-progress', 'uptime']) {
    const view = buildView(id, {time, cpu: 0.4, cores: [0.1, 0.5, 0.9, 0.3], memory: {used: 3, total: 4},
        disk: {used: 1, total: 2}, battery: {percent: 50, status: 'Charging'}, temperature: 60,
        history: {cpu: [0.2]}, uptime: 5000}, {});
    const [w, h] = canvasSize(view.chart, 400, 300);
    docs[id] = renderChart(view.chart, w, h);
    assert.ok(docs[id].startsWith('<svg') && docs[id].includes(`width="${w}"`), id);
    assert.ok(!docs[id].includes('{{'), `${id}: unfilled template tag`);
}
console.log('DOCS ' + JSON.stringify(docs));
const painted = paints;
graph.update(buildView('cpu', {cpu: 0.4, history: {cpu: [0.1, 0.9, 0.4]}}));
assert.equal(paints, painted + 1);
const month = mountWidget(adapter, buildView('calendar'));
month.update(buildView('calendar', {time}));
assert.equal(month.root.children[1].children.length, 1 + cells.length / 7);
// Legacy booleans migrate once, and only when the user customized them.
const store = (user) => ({user, list: null, get_user_value(k) { return k === 'widgets' ? this.list : (k in user ? true : null); },
    get_boolean(k) { return k in user ? user[k] : true; }, set_strv(k, v) { this.list = v; }});
const untouched = store({});
assert.equal(migrateLegacyWidgets(untouched), false);
const custom = store({'show-greeting': false, 'show-stats': false});
assert.equal(migrateLegacyWidgets(custom), true);
assert.deepEqual(custom.list, ['clock', 'today']);
assert.equal(migrateLegacyWidgets(custom), false);
assert.deepEqual(DEFAULT_WIDGETS, ['clock', 'today', 'cpu', 'memory']);
"""
        result = subprocess.run(['node', '--input-type=module', '-e', script],
                                cwd=notheme.ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        import json
        from xml.etree import ElementTree
        docs = json.loads(next(line for line in result.stdout.splitlines() if line.startswith('DOCS '))[5:])
        for name, doc in docs.items():
            ElementTree.fromstring(doc)  # raises unless the drawing is well-formed XML

    def test_template_engine_and_js_rendered_charts(self):
        script = r"""
import assert from 'node:assert/strict';
import {renderTemplate} from './extension/widgets/lib/template.js';
import {registerChart, renderChart, canvasSize} from './extension/widgets/lib/charts.js';
import {svgDocument} from './extension/widgets/lib/svg.js';
assert.equal(renderTemplate('a{{x}}b', {x: '<&>"'}), 'a&lt;&amp;&gt;&quot;b');
assert.equal(renderTemplate('{{{x}}}', {x: '<g/>'}), '<g/>');
assert.equal(renderTemplate('{{#if on}}yes{{else}}no{{/if}}', {on: 0}), 'no');
assert.equal(renderTemplate('{{#each rows}}[{{n}}{{sep}}]{{/each}}', {rows: [{n: 1}, {n: 2}], sep: ','}), '[1,][2,]');
assert.equal(renderTemplate('{{a.b}}', {a: {b: 1.23456}}), '1.235');
assert.throws(() => renderTemplate('{{#if x}}open', {}));
// A widget may skip the template and render its own SVG.
registerChart({type: 'probe', size: (_c, w) => [w, w], render: (c, w, h, theme) => svgDocument(w, h, `<rect fill="${theme.accent}"/>`)});
assert.ok(renderChart({type: 'probe'}, 50, 50).includes('<rect fill="#'));
assert.deepEqual(canvasSize({type: 'probe'}, 90, 60), [90, 90]);
"""
        result = subprocess.run(['node', '--input-type=module', '-e', script],
                                cwd=notheme.ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_widget_scaffold_registers_a_user_widget(self):
        import widgets, tempfile
        real = widgets.USER
        with tempfile.TemporaryDirectory() as tmp:
            widgets.USER = Path(tmp)
            try:
                path = widgets.create('probe-one', size='2x1', author='Ada')
                self.assertIn("id: 'probe-one'", path.read_text())
                self.assertIn("author: 'Ada'", path.read_text())
                self.assertTrue((path.parent / 'widget.svg').exists())
                self.assertIn('probeOne', (Path(tmp) / 'index.js').read_text())
                with self.assertRaises(ValueError):
                    widgets.create('probe-one')
                with self.assertRaises(ValueError):
                    widgets.create('Bad Id')
                with self.assertRaises(ValueError):
                    widgets.create('clock')
                with self.assertRaises(ValueError):
                    widgets.create('date')  # an alias of the Today widget
                (Path(tmp) / 'probe-one' / 'widget.js').write_text(path.read_text().replace("'probe-one'", "'other'", 1))
                with self.assertRaises(ValueError):
                    widgets.write_user_index()  # id differs from the folder name
            finally:
                widgets.USER = real

    def test_palette_ink_follows_the_chosen_surface(self):
        script = r"""
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {themePalette} from './extension/style.js';
import {setTheme, THEME} from './extension/widgets/index.js';
const def = JSON.parse(readFileSync('palette.json'));
const light = themePalette(def, 'dark', {surface: '#FFFFFF'});
assert.equal(light.foreground, def.modes.light.foreground);
assert.equal(light.background, '#FFFFFF');
const dark = themePalette(def, 'light', {surface: '#101010', accent: '#00AAFF', border: '#333333'});
assert.equal(dark.foreground, def.modes.dark.foreground);
assert.equal(dark.accent, '#00AAFF');
assert.equal(dark.border, '#333333');
assert.equal(themePalette(def, 'light', {surface: 'nope'}).foreground, def.modes.light.foreground);
setTheme({bg: light.background, muted: light.muted});
assert.equal(THEME.bg, '#FFFFFF');
"""
        result = subprocess.run(['node', '--input-type=module', '-e', script],
                                cwd=notheme.ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_wallpaper_settings_cover_desktop_and_match_mode_fallback(self):
        from theme import wallpaper_settings
        dark = dict(wallpaper_settings({'theme-mode': 'dark'}))
        light = dict(wallpaper_settings({'theme-mode': 'light'}))
        self.assertEqual(dark['picture-options'], 'zoom')
        self.assertEqual(light['picture-options'], 'zoom')
        self.assertEqual(dark['primary-color'], '#000000')
        self.assertEqual(light['primary-color'], '#FFFFFF')
        self.assertEqual(dark['secondary-color'], dark['primary-color'])

    def test_settings_page_validates_values_against_the_schema(self):
        import settings
        keys = settings.load_schema()
        self.assertNotIn('show-cpu', keys)
        self.assertEqual(settings.variant(keys, 'widget-x', 0.5), '0.5')
        self.assertEqual(settings.variant(keys, 'theme-mode', 'light'), "'light'")
        self.assertEqual(settings.variant(keys, 'widget-cells', ['cpu@2,1']), "['cpu@2,1']")
        for key, value in [('widget-x', 5), ('theme-mode', 'neon'), ('widget-cells', ['x;y']), ('desktop-widgets', 1)]:
            with self.assertRaises(ValueError):
                settings.variant(keys, key, value)

    def test_dropping_a_widget_on_another_pushes_it_to_the_nearest_free_cell(self):
        script = (
            "import {dropCard} from './extension/widgets/index.js';"
            "const r = dropCard(['1x1','1x1','2x1'], 4, [{col:0,row:0},{col:1,row:0},{col:0,row:1}], 2, {col:1,row:0});"
            "console.log(JSON.stringify(r));")
        result = subprocess.run(['node', '--input-type=module', '-e', script], cwd=notheme.ROOT,
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(json.loads(result.stdout), [{'col': 0, 'row': 0}, {'col': 1, 'row': 1}, {'col': 1, 'row': 0}])

    def test_gtk4_managed_block_migrates_legacy_import_and_is_idempotent(self):
        uri = 'file:///example/notheme/gtk-4.0/gtk.css'
        original = '/* user theme */\nwindow { color: white; }\n'
        legacy = f'@import url("{uri}");\n' + original
        css = 'window { background: #000000; }\n'
        result = notheme.gtk4_user_css(legacy, css, uri)
        self.assertTrue(result.startswith(original))
        self.assertNotIn(f'@import url("{uri}");', result)
        self.assertEqual(notheme.gtk4_user_css(result, css, uri), result)
        updated = notheme.gtk4_user_css(result, 'window { color: red; }', uri)
        self.assertTrue(updated.startswith(original))
        self.assertNotIn(css, updated)
        self.assertEqual(updated.count('/* >>> notheme GTK4 >>> */'), 1)
        with self.assertRaises(RuntimeError):
            notheme.gtk4_user_css('/* >>> notheme GTK4 >>> */', css, uri)

    def test_black_surfaces_and_outline_only_shell_states(self):
        import re
        css = (notheme.ROOT / 'vendor/gtk.css').read_text()
        for surface in ('window', 'view', 'headerbar', 'popover', 'dialog', 'card', 'sidebar'):
            self.assertIn(f'@define-color {surface}_bg_color #000000;', css)
        shell = (notheme.ROOT / 'extension/stylesheet.css').read_text()
        for selector, declarations in re.findall(r'([^{}]+)\{([^{}]+)\}', shell):
            fill = re.search(r'(?<![-\w])background-color:\s*(#[0-9A-Fa-f]{6})', declarations)
            if fill and fill.group(1) != '#000000':
                # Indicator dots (dock, widget meters) are the only filled marks.
                self.assertTrue('app-grid-running-dot' in selector or 'notheme-pip' in selector or 'workspace-dot' in selector or
                                'popup-separator-menu-item-separator' in selector, selector)
        self.assertIn('border-color: #D71921', shell)
        out = notheme.build()
        for state in ('on', 'off'):
            name = f'assets/toggle-{state}.svg'
            self.assertEqual((out / 'extension' / name).read_text(),
                             (out / 'theme/gnome-shell' / name).read_text())
        self.assertEqual((out / 'icons/scalable/places/user-desktop.svg').read_text(),
                         (out / 'icons/scalable/places/folder-desktop.svg').read_text())

    def test_gtk4_theme_parses_and_covers_shared_apps_and_clock_fonts(self):
        out = notheme.build()
        css = out / 'theme/gtk-4.0/gtk.css'
        result = subprocess.run(['/usr/bin/python3', '-c', '''
import gi, sys
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk
provider = Gtk.CssProvider()
errors = []
provider.connect('parsing-error', lambda p, section, error: errors.append(str(error)))
provider.load_from_path(sys.argv[1])
assert not errors, errors
''', str(css)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        content = css.read_text()
        for selector in ('#NautilusPathBar', '.boxed-list > row', '.message-dialog',
                         '.night .clock-time', '.running-stopwatch label', 'calendar label'):
            self.assertIn(selector, content)
        self.assertIn('font-family: "Doto"', content)

    def test_pixel_pack_uses_only_integer_grid_pixels(self):
        import xml.etree.ElementTree as ET
        out = notheme.build()
        icons = list((out / 'icons').rglob('*.svg'))
        self.assertGreater(len(icons), 50)
        for icon in icons:
            svg = ET.parse(icon).getroot()
            self.assertEqual(svg.attrib['viewBox'], '0 0 16 16', str(icon))
            self.assertEqual(svg.attrib['shape-rendering'], 'crispEdges')
            for pixel in svg:
                self.assertEqual(pixel.tag, '{http://www.w3.org/2000/svg}rect')
                self.assertEqual(pixel.attrib['width'], '1')
                self.assertEqual(pixel.attrib['height'], '1')
                self.assertIn(int(pixel.attrib['x']), range(16))
                self.assertIn(int(pixel.attrib['y']), range(16))
                self.assertIn(pixel.attrib['fill'], ('#F2F2F2', '#D71921', '#8C8C8C'))
                if 'symbolic' in icon.parts:
                    self.assertEqual(pixel.attrib['fill'], '#F2F2F2')
        folder = (out / 'icons/scalable/places/folder.svg').read_text()
        downloads = (out / 'icons/scalable/places/folder-download.svg').read_text()
        self.assertNotEqual(folder, downloads)

    def test_zsh_startup_block_preserves_user_config_and_is_idempotent(self):
        original = '# Existing theme\nsource ~/.oh-my-zsh/oh-my-zsh.sh\nalias ll="ls -l"\n'
        theme = Path("/home/example user/.config/notheme/zsh-theme.zsh")
        configured = notheme.zsh_rc_content(original, theme)
        self.assertTrue(configured.startswith(original))
        self.assertIn("source '/home/example user/.config/notheme/zsh-theme.zsh'", configured)
        self.assertEqual(notheme.zsh_rc_content(configured, theme), configured)
        self.assertEqual(configured.count('# >>> notheme prompt >>>'), 1)
        with self.assertRaises(RuntimeError):
            notheme.zsh_rc_content('# >>> notheme prompt >>>\n', theme)

    def test_terminal_chrome_and_dark_variant_are_bundled(self):
        out = notheme.build()
        css = (out / 'theme/gtk-3.0/gtk.css').read_text()
        self.assertIn('terminal-window headerbar:backdrop', css)
        self.assertIn('terminal-window notebook > header tab:checked', css)
        # GNOME Terminal's window node is terminal-window, not window.
        self.assertIn('terminal-window.csd decoration,', css)
        self.assertIn('terminal-window.csd, terminal-window.csd:backdrop {', css)
        self.assertNotIn('window.terminal-window', css)
        self.assertEqual((out / 'theme/gtk-3.0/gtk-dark.css').read_text(), '@import url("gtk.css");\n')

    def test_dashboard_preferences_schema_defaults_and_ranges(self):
        Gio, GLib = notheme.gio()
        out = notheme.build()
        source = Gio.SettingsSchemaSource.new_from_directory(
            str(out / 'extension/schemas'), Gio.SettingsSchemaSource.get_default(), False)
        schema = source.lookup('org.gnome.shell.extensions.notheme', False)
        for key in ('show-date', 'show-greeting', 'show-stats'):
            self.assertTrue(schema.get_key(key).get_default_value().unpack())
        self.assertEqual(schema.get_key('clock-format').get_default_value().unpack(), '24h')
        self.assertFalse(schema.get_key('clock-seconds').get_default_value().unpack())
        self.assertFalse(schema.has_key('widget-scale'))
        self.assertFalse(schema.get_key('clock-format').range_check(GLib.Variant('s', 'invalid')))

    def test_shell_theme_is_discoverable_without_extension_scope(self):
        out = notheme.build()
        css = (out / 'theme/gnome-shell/gnome-shell.css').read_text()
        self.assertIn('@import url("file:///usr/share/themes/Yaru-dark/gnome-shell/gnome-shell.css")', css)
        self.assertNotIn('.notheme-shell', css)
        self.assertIn('stage {', css)
        self.assertIn('.calendar .calendar-day.calendar-today', css)
        self.assertIn('.quick-toggle-has-menu .quick-toggle-menu-button:checked', css)

    def test_cursor_theme_validation_and_inheritance(self):
        with tempfile.TemporaryDirectory(prefix='notheme-cursors-') as tmp:
            root = Path(tmp)
            cursors = root / 'icons/White/cursors'
            cursors.mkdir(parents=True)
            (cursors / 'left_ptr').write_bytes(b'cursor fixture')
            wrapper = root / 'icons/Wrapper'
            wrapper.mkdir()
            (wrapper / 'index.theme').write_text('[Icon Theme]\nInherits=White\n')
            loop = root / 'icons/Loop'
            loop.mkdir()
            (loop / 'index.theme').write_text('[Icon Theme]\nInherits=Loop\n')
            with patch.object(notheme, 'paths', return_value={'data': root}), \
                    patch.object(Path, 'home', return_value=root), \
                    patch.dict(os.environ, {'XDG_DATA_DIRS': tmp, 'XCURSOR_PATH': ''}):
                self.assertTrue(notheme.cursor_theme_exists('White'))
                self.assertTrue(notheme.cursor_theme_exists('Wrapper'))
                self.assertFalse(notheme.cursor_theme_exists('Loop'))
                self.assertFalse(notheme.cursor_theme_exists('Missing'))
                self.assertFalse(notheme.cursor_theme_exists('../White'))

    def test_cursor_keep_preserves_size_and_selected_cursor_uses_24px(self):
        import argparse
        args = argparse.Namespace(cursor='keep', dock=False)
        self.assertFalse(any('cursor-' in key for _, key, _ in notheme.desktop_settings(args)))
        args.cursor = 'DMZ-White'
        values = notheme.desktop_settings(args)
        self.assertIn(('org.gnome.desktop.interface', 'cursor-theme', 'DMZ-White'), values)
        self.assertIn(('org.gnome.desktop.interface', 'cursor-size', 24), values)

    def test_flat_red_calendar_and_clock_styles(self):
        css = (notheme.ROOT / 'extension/stylesheet.css').read_text()
        for selector in ('.calendar .calendar-day.calendar-today',
                         '.calendar .calendar-day:selected',
                         '.world-clocks-button .world-clocks-time',
                         '#panel .clock-display .clock'):
            self.assertIn(selector, css)
        self.assertNotIn('box-shadow: 0 ', css)
        self.assertIn('-barlevel-active-background-color: #D71921', css)

    def test_core_dock_icons_are_bundled_and_declared(self):
        import configparser
        out = notheme.build()
        index = configparser.ConfigParser()
        index.read(out / 'icons/index.theme')
        directories = index['Icon Theme']['Directories'].split(',')
        for name in ('org.gnome.Nautilus', 'brave-browser', 'brave-browser-stable',
                     'com.brave.Browser', 'code', 'com.visualstudio.code',
                     'org.gnome.Terminal', 'utilities-terminal', 'kitty'):
            self.assertTrue((out / f'icons/scalable/apps/{name}.svg').exists(), name)
        self.assertIn('scalable/apps', directories)
        self.assertIn('symbolic/actions', directories)
        for directory in directories:
            self.assertIn(directory, index)
        for name in ('user-trash', 'user-trash-full'):
            self.assertTrue((out / f'icons/scalable/places/{name}.svg').exists())
        self.assertTrue((out / 'icons/symbolic/actions/view-app-grid-symbolic.svg').exists())

    def test_shell_split_toggle_styles_cover_both_directions_and_states(self):
        css = (notheme.ROOT / 'extension/stylesheet.css').read_text()
        for selector in ('.quick-toggle-has-menu .quick-toggle:ltr',
                         '.quick-toggle-has-menu .quick-toggle:rtl',
                         '.quick-toggle-has-menu .quick-toggle-menu-button:checked',
                         '.quick-toggle-has-menu .quick-toggle-menu-button:checked:hover'):
            self.assertIn(selector, css)
        self.assertIn('-slider-handle-border-color: #F2F2F2', css)

    def test_generated_assets_are_valid(self):
        import xml.etree.ElementTree as ET
        out = notheme.build()
        for svg in out.rglob('*.svg'):
            if 'widgets' in svg.parts:
                continue  # widget drawings are templates; test_widget_catalog checks their rendered output
            ET.parse(svg)
        metadata = json.loads((out / 'extension/metadata.json').read_text())
        self.assertEqual(metadata['uuid'], notheme.UUID)
        self.assertTrue((out / 'extension/schemas/gschemas.compiled').exists())
        kitty = (out / 'apps/kitty.conf').read_text()
        self.assertNotIn('shell fish', kitty)
        self.assertNotIn('demonshot', kitty)

    def test_gtk3_theme_parses_with_its_resource_bundle(self):
        import gi
        gi.require_version('Gtk', '3.0')
        from gi.repository import Gio, Gtk
        out = notheme.build()
        theme = out / 'theme/gtk-3.0'
        resource = Gio.Resource.load(str(theme / 'gtk.gresource'))
        Gio.resources_register(resource)
        try:
            provider = Gtk.CssProvider()
            errors = []
            provider.connect('parsing-error', lambda p, section, error: errors.append(str(error)))
            provider.load_from_path(str(theme / 'gtk.css'))
            self.assertEqual(errors, [])
        finally:
            Gio.resources_unregister(resource)


class IntegrationTests(unittest.TestCase):
    def test_cli_apply_and_restore_in_isolated_home(self):
        # The keyfile backend cannot reach the real shell's dconf backend. All
        # data/config/cache paths are isolated, even for fontconfig subprocesses.
        with tempfile.TemporaryDirectory(prefix='notheme-integration-') as tmp:
            home = Path(tmp)
            env = dict(os.environ, HOME=tmp, GSETTINGS_BACKEND='keyfile',
                       ZDOTDIR=tmp,
                       XDG_DATA_HOME=str(home / 'data'), XDG_CONFIG_HOME=str(home / 'config'),
                       XDG_STATE_HOME=str(home / 'state'), XDG_CACHE_HOME=str(home / 'cache'))
            config = home / 'config'
            zshrc = home / '.zshrc'
            zshrc.write_text('# Existing startup\nalias ll="ls -l"\n')
            (config / 'gtk-4.0').mkdir(parents=True)
            (config / 'gtk-4.0/gtk.css').write_text('/* my original CSS */\n')
            (config / 'gtk-3.0').mkdir()
            (config / 'gtk-3.0/gtk.css').write_text('button { border-radius: 999px; }\n')
            (config / 'btop').mkdir()
            (config / 'btop/btop.conf').write_text('color_theme = "Default"\nupdate_ms = 2500\n')
            command = [str(notheme.ROOT / 'notheme')]
            def background_setting(key):
                return subprocess.check_output(['gsettings', 'get', 'org.gnome.desktop.background', key],
                                               env=env, text=True).strip()
            for key, value in [('picture-options', 'centered'), ('primary-color', '#2c001e')]:
                subprocess.run(['gsettings', 'set', 'org.gnome.desktop.background', key, value], env=env, check=True)
            args = ['apply', '--yes', '--all']
            applied = subprocess.run(command + args, env=env, capture_output=True, text=True)
            self.assertEqual(applied.returncode, 0, applied.stdout + applied.stderr)
            self.assertNotIn('Gio.Settings.range_check is deprecated', applied.stderr)
            self.assertEqual(background_setting('picture-options'), "'zoom'")
            self.assertEqual(background_setting('primary-color'), "'#000000'")
            self.assertTrue((home / f'data/gnome-shell/extensions/{notheme.UUID}/extension.js').exists())
            self.assertIn('update_ms = 2500', (config / 'btop/btop.conf').read_text())
            self.assertIn('/* my original CSS */', (config / 'gtk-4.0/gtk.css').read_text())
            self.assertIn('/* >>> notheme GTK3 >>> */', (config / 'gtk-3.0/gtk.css').read_text())
            self.assertIn('# Existing startup', zshrc.read_text())
            self.assertIn('notheme/zsh-theme.zsh', zshrc.read_text())
            runtime = home / 'data/notheme/style-runtime'
            changed = subprocess.run(['gsettings', '--schemadir', str(runtime / 'extension/schemas'),
                                      'set', 'org.gnome.shell.extensions.notheme', 'theme-mode', 'light'],
                                     env=env, capture_output=True, text=True)
            self.assertEqual(changed.returncode, 0, changed.stderr)
            # The app renderer must repair old fitting too, not just the CLI.
            for key, value in [('picture-options', 'centered'), ('primary-color', '#2c001e')]:
                subprocess.run(['gsettings', 'set', 'org.gnome.desktop.background', key, value], env=env, check=True)
            refreshed = subprocess.run(['/usr/bin/python3', str(runtime / 'tools/theme.py')],
                                       env=env, capture_output=True, text=True)
            self.assertEqual(refreshed.returncode, 0, refreshed.stdout + refreshed.stderr)
            self.assertEqual(background_setting('picture-options'), "'zoom'")
            self.assertEqual(background_setting('primary-color'), "'#FFFFFF'")
            self.assertIn('@define-color window_bg_color #FFFFFF;',
                          (home / 'data/themes/notheme/gtk-4.0/gtk.css').read_text())
            self.assertIn('fill="#161616"', (home / 'data/icons/notheme/scalable/apps/code.svg').read_text())
            self.assertIn('fill="#FFFFFF"', (home / 'data/backgrounds/notheme-light.svg').read_text())
            self.assertIn('fill="#000000"', (home / 'data/backgrounds/notheme-dark.svg').read_text())
            self.assertIn('@define-color window_bg_color #FFFFFF;',
                          (home / 'data/themes/notheme-light/gtk-3.0/gtk.css').read_text())
            def setting(key):
                return subprocess.check_output(['gsettings', 'get', 'org.gnome.desktop.interface', key],
                                               env=env, text=True).strip()
            self.assertEqual(setting('gtk-theme'), "'notheme-light'")
            # A distinct icon-theme name makes running apps reload icons at once.
            self.assertEqual(setting('icon-theme'), "'notheme-light'")
            light_index = (home / 'data/icons/notheme-light/index.theme').read_text()
            self.assertIn('Inherits=Papirus-Light,', light_index)
            subprocess.run(['gsettings', 'set', 'org.gnome.desktop.interface', 'color-scheme', 'prefer-dark'],
                           env=env, check=True)
            dark = subprocess.run(['/usr/bin/python3', str(runtime / 'tools/theme.py'), '--follow-system'],
                                  env=env, capture_output=True, text=True)
            self.assertEqual(dark.returncode, 0, dark.stdout + dark.stderr)
            self.assertEqual(setting('gtk-theme'), "'notheme'")
            self.assertEqual(setting('icon-theme'), "'notheme'")
            self.assertIn('Inherits=Papirus-Dark,', (home / 'data/icons/notheme/index.theme').read_text())
            self.assertEqual(setting('color-scheme'), "'prefer-dark'")
            self.assertIn('@define-color window_bg_color #000000;',
                          (home / 'data/themes/notheme/gtk-3.0/gtk.css').read_text())
            undo_dark = subprocess.run(command + ['restore'], env=env, capture_output=True, text=True)
            self.assertEqual(undo_dark.returncode, 0, undo_dark.stdout + undo_dark.stderr)
            # Restore the system choice made outside the installer transaction.
            subprocess.run(['gsettings', 'set', 'org.gnome.desktop.interface', 'color-scheme', 'prefer-light'],
                           env=env, check=True)
            # First undo the preferences Apply transaction, then the initial install.
            refresh_restored = subprocess.run(command + ['restore'], env=env, capture_output=True, text=True)
            self.assertEqual(refresh_restored.returncode, 0, refresh_restored.stdout + refresh_restored.stderr)
            restored = subprocess.run(command + ['restore'], env=env, capture_output=True, text=True)
            self.assertEqual(restored.returncode, 0, restored.stdout + restored.stderr)
            self.assertEqual(background_setting('picture-options'), "'centered'")
            self.assertEqual(background_setting('primary-color'), "'#2c001e'")
            self.assertFalse((home / f'data/gnome-shell/extensions/{notheme.UUID}').exists())
            self.assertEqual((config / 'gtk-4.0/gtk.css').read_text(), '/* my original CSS */\n')
            self.assertEqual((config / 'gtk-3.0/gtk.css').read_text(), 'button { border-radius: 999px; }\n')
            self.assertEqual((config / 'btop/btop.conf').read_text(), 'color_theme = "Default"\nupdate_ms = 2500\n')
            self.assertEqual(zshrc.read_text(), '# Existing startup\nalias ll="ls -l"\n')


if __name__ == '__main__':
    unittest.main()
