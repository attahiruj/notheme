// Parse both live modes with GNOME Shell's actual CSS parser; no shell restart.
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import St from 'gi://St';
import {styleCSS, themePalette, recolorCSS, radiusCSS, prioritizeCSS} from '../extension/style.js';
import {replaceStylesheet, unloadStylesheet} from '../extension/style-lifecycle.js';

const directory = Gio.File.new_for_path(GLib.get_current_dir()).get_child('build/extension');
const read = name => {
    const [, data] = directory.get_child(name).load_contents(null);
    return new TextDecoder().decode(data);
};
const definition = JSON.parse(read('palette.json'));
const base = read('stylesheet.css').replace(/url\("assets\/([^"]+)"\)/g,
    (_, name) => `url("${directory.get_child(`assets/${name}`).get_uri()}")`);
const file = Gio.File.new_for_path(`${GLib.get_tmp_dir()}/notheme-style-${GLib.get_real_time()}.css`);
try {
    for (const mode of ['dark', 'light']) {
        for (const selection of ['outline', 'filled']) {
            const p = themePalette(definition, mode);
            const css = prioritizeCSS(radiusCSS(recolorCSS(base, definition, p), 16) + styleCSS({
                accent: p.accent, surface: p.background, foreground: p.foreground,
                border: p.border, selection, radius: 16, clockFont: 'Doto',
            }));
            GLib.file_set_contents(file.get_path(), css);
            const theme = new St.Theme();
            theme.load_stylesheet(file);
            theme.unload_stylesheet(file);
        }
    }
} finally {
    file.delete(null);
}
print('Dark/light and outline/filled styles parsed with St.Theme.');

// Reproduce Shell's custom-sheet inheritance, without constructing any actors
// or a ThemeContext (those require a compositor and must not be probed here).
const before = new St.Theme();
const after = new St.Theme();
const oldFile = Gio.File.new_for_path(`${GLib.get_tmp_dir()}/notheme-old-${GLib.get_real_time()}.css`);
const newFile = Gio.File.new_for_path(`${GLib.get_tmp_dir()}/notheme-new-${GLib.get_real_time()}.css`);
try {
    GLib.file_set_contents(oldFile.get_path(), '.example { border-radius: 4px; }');
    GLib.file_set_contents(newFile.get_path(), '.example { border-radius: 28px; }');
    before.load_stylesheet(oldFile);
    for (const inherited of before.get_custom_stylesheets()) after.load_stylesheet(inherited);
    replaceStylesheet(before, after, oldFile, newFile);
    const active = after.get_custom_stylesheets();
    if (active.length !== 1 || !active[0].equal(newFile) || before.get_custom_stylesheets().length)
        throw new Error('Runtime stylesheet inheritance was not cleaned up');
    unloadStylesheet(after, after, newFile);
    if (after.get_custom_stylesheets().length)
        throw new Error('Disable left a runtime stylesheet behind');
} finally {
    before.unload_stylesheet(oldFile);
    after.unload_stylesheet(oldFile);
    after.unload_stylesheet(newFile);
    oldFile.delete(null);
    newFile.delete(null);
}
print('Native stylesheet inheritance, replacement and unload checks passed.');
