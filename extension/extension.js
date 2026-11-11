import Clutter from 'gi://Clutter';
import Cogl from 'gi://Cogl';
import Gio from 'gi://Gio';
import GdkPixbuf from 'gi://GdkPixbuf';
import GLib from 'gi://GLib';
import St from 'gi://St';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import {styleCSS, themePalette, clockFont, recolorCSS, radiusCSS, prioritizeCSS, toggleSVG} from './style.js';
import {replaceStylesheet, unloadStylesheet} from './style-lifecycle.js';
import {placeDesktop, desktopVisible} from './desktop-layer.js';
import {buildView, loadTemplates, migrateLegacyWidgets, mountWidget, normalizeWidgets, fitColumns, fitRows, packCards, parseCells, setTheme, sizeOf, spanSize, THEME,
    widgetInfo} from './widgets/index.js';
import {Sampler} from './sampler.js';

function paintImage(actor) {
    try {
        const svg = actor._render();
        if (!svg || svg === actor._svg) return; // unchanged since the last paint
        actor._svg = svg;
        const [width, height] = actor._size;
        // Rasterize at the monitor's real scale. With fractional scaling (1.33 here) the theme's scale_factor is a
        // whole number, so a drawing made at that size would be stretched on screen and look soft.
        const scale = Math.max(Main.layoutManager.primaryMonitor?.geometry_scale ?? 1,
            St.ThemeContext.get_for_stage(global.stage).scale_factor);
        const stream = Gio.MemoryInputStream.new_from_bytes(new GLib.Bytes(new TextEncoder().encode(svg)));
        const pixbuf = GdkPixbuf.Pixbuf.new_from_stream_at_scale(stream, Math.round(width * scale), Math.round(height * scale), true, null);
        stream.close(null);
        const image = new St.ImageContent({preferred_width: pixbuf.get_width(), preferred_height: pixbuf.get_height()});
        // Newer Mutter (GNOME 50) takes the Cogl context as the first argument.
        image.set_bytes(global.stage.context.get_backend().get_cogl_context(), pixbuf.read_pixel_bytes(), pixbuf.get_has_alpha() ? Cogl.PixelFormat.RGBA_8888 : Cogl.PixelFormat.RGB_888,
            pixbuf.get_width(), pixbuf.get_height(), pixbuf.get_rowstride());
        actor.content = image;
    } catch (error) {
        console.error(`notheme: chart: ${error.message}`);
    }
}

const ST_ADAPTER = {
    box: (vertical, style_class) => new St.BoxLayout({vertical, style_class}),
    label: (text, style_class) => new St.Label({text, style_class}),
    dot: style_class => new St.Widget({style_class}),
    size: (actor, width, height) => actor.set_size(width, height),
    // A widget's drawing is an SVG document; rasterize it at the display scale and show it as the actor's content.
    image: (width, height, render) => {
        const actor = new St.Widget({width, height, x_align: Clutter.ActorAlign.CENTER, y_align: Clutter.ActorAlign.CENTER,
            content_gravity: Clutter.ContentGravity.RESIZE_ASPECT});
        actor._render = render;
        actor._size = [width, height];
        paintImage(actor);
        return actor;
    },
    spacer: () => new St.Widget({y_expand: true}),
    center: actor => { actor.x_align = Clutter.ActorAlign.CENTER; },
    start: actor => { actor.x_align = Clutter.ActorAlign.START; },
    middle: actor => {
        actor.set({x_align: Clutter.ActorAlign.CENTER, y_align: Clutter.ActorAlign.CENTER, x_expand: true, y_expand: true});
    },
    redraw: actor => paintImage(actor),
    setText: (label, text) => { if (label.text !== text) label.text = text; },
    setClass: (actor, style_class) => { if (actor.style_class !== style_class) actor.style_class = style_class; },
    append: (parent, child) => parent.add_child(child),
    clear: parent => parent.destroy_all_children(),
};

const text = path => {
    try {
        const [ok, data] = GLib.file_get_contents(path);
        return ok ? new TextDecoder().decode(data) : '';
    } catch {
        return '';
    }
};

export default class Notheme extends Extension {
    enable() {
        this._signals = [];
        loadTemplates(path => text(`${this.path}/widgets/${path}`));
        this._sampler = new Sampler();
        this._mounted = [];
        this._settings = this.getSettings();
        migrateLegacyWidgets(this._settings);
        this._overviewActive = Main.overview.visible;
        this._interfaceSettings = new Gio.Settings({schema_id: 'org.gnome.desktop.interface'});
        // GNOME's Dark Style toggle is authoritative when the extension starts.
        this._syncSystemMode();
        this._connect(this._interfaceSettings, 'changed::color-scheme', () => this._syncSystemMode());
        this._connect(this._settings, 'changed::theme-mode', () => {
            this._syncThemeMode();
            this._queueAppStyleRefresh();
        });
        this._palette = JSON.parse(text(`${this.path}/palette.json`));
        const themeContext = St.ThemeContext.get_for_stage(global.stage);
        this._connect(themeContext, 'changed', () => {
            if (!this._applyingStyle && this._styleTheme && themeContext.get_theme() !== this._styleTheme)
                this._queueStyleRefresh();
        });
        this._connect(this._settings, 'changed', () => {
            if (this._rebuildSource) return;
            // Coalesce slider drags instead of rebuilding widgets/styles at
            // every pointer event. Native theme-change refresh stays deferred.
            this._rebuildSource = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 120, () => {
                this._rebuildSource = null;
                this._rebuild();
                return GLib.SOURCE_REMOVE;
            });
        });
        this._connect(Main.layoutManager, 'monitors-changed', () => this._rebuild());
        this._connect(Main.sessionMode, 'updated', () => this._applyMode());
        this._connect(global.display, 'restacked', () => this._restackDesktop());
        this._connect(Main.overview, 'showing', () => {
            this._overviewActive = true;
            this._syncDesktopVisibility();
        });
        this._connect(Main.overview, 'hidden', () => {
            this._overviewActive = false;
            this._syncDesktopVisibility();
        });
        this._rebuild();
        this._timer = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 1, () => {
            this._update();
            return GLib.SOURCE_CONTINUE;
        });
        this._queueAppStyleRefresh();
    }

    _connect(object, signal, callback) {
        this._signals.push([object, object.connect(signal, callback)]);
    }

    _syncSystemMode() {
        const mode = this._interfaceSettings.get_string('color-scheme') === 'prefer-dark' ? 'dark' : 'light';
        if (this._settings.get_string('theme-mode') !== mode)
            this._settings.set_string('theme-mode', mode);
    }

    _syncThemeMode() {
        const mode = this._settings.get_string('theme-mode');
        const systemDark = this._interfaceSettings.get_string('color-scheme') === 'prefer-dark';
        // Compare effective modes so GNOME's "default" remains untouched in light mode.
        if (systemDark !== (mode === 'dark'))
            this._interfaceSettings.set_string('color-scheme', mode === 'dark' ? 'prefer-dark' : 'prefer-light');
    }

    _queueAppStyleRefresh() {
        this._appStylePending = true;
        if (this._appStyleSource || this._appStyleProcess) return;
        this._appStyleSource = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 300, () => {
            this._appStyleSource = null;
            this._appStylePending = false;
            const script = Gio.File.new_for_path(GLib.build_filenamev([
                GLib.get_user_data_dir(), 'notheme', 'style-runtime', 'tools', 'theme.py',
            ]));
            if (!script.query_exists(null)) return GLib.SOURCE_REMOVE;
            try {
                const process = Gio.Subprocess.new(
                    ['/usr/bin/python3', '-B', script.get_path(), '--follow-system'],
                    Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_PIPE);
                this._appStyleProcess = process;
                process.communicate_utf8_async(null, null, (proc, result) => {
                    try {
                        const [, out, err] = proc.communicate_utf8_finish(result);
                        if (!proc.get_successful())
                            console.error(`notheme: app appearance refresh failed: ${(err || out).trim()}`);
                    } catch (error) {
                        console.error(`notheme: ${error.message}`);
                    }
                    this._appStyleProcess = null;
                    if (this._settings && this._appStylePending) this._queueAppStyleRefresh();
                });
            } catch (error) {
                this._appStyleProcess = null;
                console.error(`notheme: ${error.message}`);
            }
            return GLib.SOURCE_REMOVE;
        });
    }

    _rebuild() {
        this._applyStyle();
        this._desktop?.destroy();
        this._desktop = null;
        this._mounted = [];
        const monitor = Main.layoutManager.primaryMonitor;
        const size = monitor ? `${monitor.width}x${monitor.height}` : '';
        if (size && this._settings.get_string('monitor-size') !== size)
            this._settings.set_string('monitor-size', size);
        if (monitor && this._settings.get_boolean('desktop-widgets')) {
            const scale = Math.min(monitor.width / 1920, monitor.height / 1080, 1.4);
            // Dedicated desktop layer above wallpapers, below all window actors.
            this._desktop = new St.BoxLayout({vertical: true, reactive: false,
                style_class: `notheme-desktop notheme-cards-${this._settings.get_string('card-style')}`,
                style: `spacing: ${Math.round(this._settings.get_int('widget-gap') * scale)}px;`,
                opacity: Math.round(255 * this._settings.get_double('widget-opacity'))});
            const anchor = this._settings.get_string('widget-anchor');
            const align = anchor.endsWith('right') ? Clutter.ActorAlign.END
                : anchor === 'center' ? Clutter.ActorAlign.CENTER : Clutter.ActorAlign.START;
            const marginX = Math.round(monitor.width * this._settings.get_double('widget-x'));
            const marginY = Math.round(monitor.height * this._settings.get_double('widget-y'));
            // The box grows as text changes, so re-anchor whenever its size does.
            const place = () => {
                const [width, height] = this._desktop.get_size();
                const x = anchor.endsWith('left') ? marginX
                    : anchor.endsWith('right') ? monitor.width - width - marginX : (monitor.width - width) / 2;
                const y = anchor.startsWith('top') ? marginY
                    : anchor.startsWith('bottom') ? monitor.height - height - marginY : (monitor.height - height) / 2;
                this._desktop.set_position(monitor.x + Math.round(x), monitor.y + Math.round(y));
            };
            this._desktop.connect('notify::width', place);
            this._desktop.connect('notify::height', place);
            place();
            // Hide cards on small displays rather than overlap the dock or clip text.
            const roomy = monitor.width >= 1100 && monitor.height >= 720;
            // The grid is as wide as the display allows, keeping the side margin on both edges.
            const columns = fitColumns(anchor === 'center' ? monitor.width * 0.9 : monitor.width - 2 * marginX);
            const maxRows = fitRows(anchor === 'center' ? monitor.height * 0.9 : monitor.height - marginY);
            const options = this._widgetOptions();
            const pinned = parseCells(this._settings.get_strv('widget-cells'));
            let run = null;
            const flush = () => {
                if (!run) return;
                // Cards sit on a fixed grid: every card is 1x1, 1x2, 2x1 or 2x2 units.
                const {cells, rows} = packCards(run.map(([id]) => sizeOf(id)), columns,
                    run.map(([id]) => pinned.get(id) ?? null), maxRows);
                const used = Math.max(...cells.map(c => c.col + c.cols));
                const grid = new St.Widget({x_align: align, width: spanSize(used), height: spanSize(rows)});
                run.forEach(([, mounted], i) => {
                    mounted.root.set_position(cells[i].col * (THEME.unit + THEME.gap), cells[i].row * (THEME.unit + THEME.gap));
                    grid.add_child(mounted.root);
                });
                this._desktop.add_child(grid);
                run = null;
            };
            for (const id of normalizeWidgets(this._settings.get_strv('widgets'))) {
                const card = widgetInfo(id).kind === 'card';
                if (card && !roomy) continue;
                const mounted = mountWidget(ST_ADAPTER, buildView(id, {}, options));
                if (id === 'clock') {
                    // The clock owns two grid blocks; shrink the font so the text fits them.
                    const chars = Math.max(5, buildView(id, {}, options).text.length);
                    const fit = Math.floor(spanSize(2) / (chars * 0.62));
                    const size = Math.round(this._settings.get_int('desktop-clock-size') * scale);
                    mounted.root.style = `font-size: ${Math.max(32, Math.min(size, fit))}px;`;
                }
                (run ??= []).push([id, mounted]);
                this._mounted.push([id, mounted]);
            }
            flush();
            this._restackDesktop();
        }
        this._applyMode();
        this._update();
    }

    _applyMode() {
        this._locked = Main.sessionMode.isLocked || Main.sessionMode.currentMode === 'unlock-dialog';
        const group = Main.layoutManager.uiGroup;
        group.remove_style_class_name('notheme-shell');
        group.remove_style_class_name('notheme-lock');
        if (this._locked) {
            if (this._settings.get_boolean('lock-style'))
                group.add_style_class_name('notheme-lock');
        } else if (this._settings.get_boolean('shell-style')) {
            group.add_style_class_name('notheme-shell');
        }
        this._syncDesktopVisibility();
    }

    _restackDesktop() {
        placeDesktop(this._desktop, global.window_group, Main.layoutManager._backgroundGroup);
    }

    _syncDesktopVisibility() {
        if (this._desktop)
            this._desktop.visible = desktopVisible(this._locked, this._overviewActive);
    }

    _applyStyle() {
        if (this._applyingStyle) return;
        this._applyingStyle = true;
        try {
            this._loadStyle();
        } finally {
            this._applyingStyle = false;
        }
    }

    _queueStyleRefresh() {
        // Never load/unload stylesheets from inside St.ThemeContext::changed.
        // Let Shell finish copying styles and replacing the native theme first.
        if (this._styleRefreshSource) return;
        this._styleRefreshSource = GLib.idle_add(GLib.PRIORITY_DEFAULT_IDLE, () => {
            this._styleRefreshSource = null;
            if (this._settings) this._applyStyle();
            return GLib.SOURCE_REMOVE;
        });
    }

    _loadStyle() {
        const s = this._settings;
        const p = themePalette(this._palette, s.get_string('theme-mode'), {
            accent: s.get_string('accent-color'), surface: s.get_string('surface-color'),
            border: s.get_string('border-color'),
        });
        const radius = s.get_int('corner-radius');
        const values = {
            accent: p.accent, surface: p.background, foreground: p.foreground,
            border: p.border, radius,
            fontSize: s.get_int('shell-font-size'), panelHeight: s.get_int('panel-height'),
            panelClockSize: s.get_int('panel-clock-size'), panelIconSize: s.get_int('panel-icon-size'), lockClockSize: s.get_int('lock-clock-size'),
            clockFont: s.get_string('clock-font'), selection: s.get_string('selection-style'),
            uiFont: s.get_string('ui-font'), outlineWidth: s.get_int('outline-width'),
            popupPadding: s.get_int('popup-padding'), panelPadding: s.get_int('panel-padding'),
            widgetGap: s.get_int('widget-gap'), cardPadding: s.get_int('card-padding'),
            scrollbarWidth: s.get_int('scrollbar-width'), scrollbarOpacity: s.get_double('scrollbar-opacity'),
            scrollbarStyle: s.get_string('scrollbar-style'),
            dotShape: s.get_string('dot-shape'),
        };
        setTheme({bg: p.background, fg: p.foreground, dim: p.secondary, muted: p.muted, line: p.border, accent: p.accent,
            font: clockFont(values.clockFont), unit: 150, gap: values.widgetGap,
            pad: s.get_string('card-style') === 'borderless' ? 0 : values.cardPadding, border: s.get_string('card-style') === 'borderless' ? 0 : values.outlineWidth,
            square: values.dotShape === 'square'});
        const currentTheme = St.ThemeContext.get_for_stage(global.stage).get_theme();
        const signature = JSON.stringify(values);
        if (this._styleFile && this._styleTheme === currentTheme && signature === this._styleSignature)
            return;

        const path = GLib.build_filenamev([GLib.get_user_cache_dir(), this.uuid, `style-${GLib.uuid_string_random()}`]);
        const bundle = {directory: Gio.File.new_for_path(path), assets: [], file: null};
        GLib.mkdir_with_parents(path, 0o700);
        try {
            let base = radiusCSS(recolorCSS(text(`${this.path}/stylesheet.css`), this._palette, p), radius);
            for (const active of [false, true]) {
                const state = active ? 'on' : 'off';
                const file = bundle.directory.get_child(`toggle-${state}.svg`);
                GLib.file_set_contents(file.get_path(), toggleSVG(p, active, radius));
                bundle.assets.push(file);
                base = base.replace(`url("assets/toggle-${state}.svg")`, `url("${file.get_uri()}")`);
            }
            bundle.file = bundle.directory.get_child('runtime.css');
            GLib.file_set_contents(bundle.file.get_path(), prioritizeCSS(base + styleCSS(values)));
            replaceStylesheet(this._styleTheme, currentTheme, this._styleFile, bundle.file);
        } catch (error) {
            this._releaseStyleBundle(bundle);
            throw error;
        }
        const previousBundle = this._styleBundle;
        this._styleBundle = bundle;
        this._styleFile = bundle.file;
        this._styleTheme = currentTheme;
        this._styleSignature = signature;
        this._releaseStyleBundle(previousBundle);
    }

    _releaseStyleBundle(bundle) {
        if (!bundle) return;
        for (const file of [...bundle.assets, bundle.file, bundle.directory]) {
            if (file) {
                try { file.delete(null); } catch { /* Cache already removed. */ }
            }
        }
    }

    _widgetOptions() {
        return {
            twelve: this._settings.get_string('clock-format') === '12h',
            seconds: this._settings.get_boolean('clock-seconds'),
            name: this._settings.get_string('greeting-name').trim(),
            titles: this._settings.get_boolean('widget-titles'),
        };
    }

    _update() {
        if (this._locked)
            return;
        const ids = new Set(this._mounted.map(([id]) => id));
        const sample = this._sampler.sample(ids);
        const options = this._widgetOptions();
        for (const [id, mounted] of this._mounted)
            mounted.update(buildView(id, sample, options));
    }

    disable() {
        if (this._appStyleSource) GLib.source_remove(this._appStyleSource);
        this._appStyleSource = null;
        this._appStylePending = false;
        if (this._styleRefreshSource) GLib.source_remove(this._styleRefreshSource);
        this._styleRefreshSource = null;
        if (this._rebuildSource) GLib.source_remove(this._rebuildSource);
        this._rebuildSource = null;
        if (this._timer)
            GLib.source_remove(this._timer);
        this._timer = null;
        for (const [object, id] of this._signals ?? [])
            object.disconnect(id);
        this._signals = [];
        Main.layoutManager.uiGroup.remove_style_class_name('notheme-shell');
        Main.layoutManager.uiGroup.remove_style_class_name('notheme-lock');
        unloadStylesheet(this._styleTheme, St.ThemeContext.get_for_stage(global.stage).get_theme(), this._styleFile);
        this._releaseStyleBundle(this._styleBundle);
        this._styleFile = this._styleTheme = null;
        this._styleBundle = this._styleSignature = null;
        this._desktop?.destroy();
        this._desktop = this._settings = null;
        this._mounted = [];
        this._sampler = null;
        this._interfaceSettings = this._palette = null;
    }
}
