"""Shared palette renderer and explicit, transactional application-theme refresh.

The CSS files are the single structural templates. palette.json owns mode colors;
the extension schema owns customization defaults. No separate light CSS fork.
"""
import json
from pathlib import Path
import re
import sys

# Installed renderer files are transaction-managed. Python caches must not make
# the runtime look user-modified and block a later drift-aware restore.
if __name__ == '__main__':
    sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
COLOR = re.compile(r'^#[0-9a-fA-F]{6}$')

# Desktop Icons NG owns a full-screen GTK window, not a normal app surface.
# User CSS has higher priority than DING's application CSS, so its transparent
# desktop must be explicitly preserved after the shared application overrides.
DESKTOP_TRANSPARENCY = '''
window.desktopwindow, window.desktopwindow.background,
window.desktopwindow.background.csd,
window.desktopwindow:backdrop, window.desktopwindow.background:backdrop,
window.desktopwindow.background.csd:backdrop {
    background: transparent; border: none; border-radius: 0; box-shadow: none;
}
'''


def read_style(schema_dir):
    from gi.repository import Gio
    if not (Path(schema_dir) / 'gschemas.compiled').exists():
        return {}
    source = Gio.SettingsSchemaSource.new_from_directory(
        str(schema_dir), Gio.SettingsSchemaSource.get_default(), False)
    schema = source.lookup('org.gnome.shell.extensions.notheme', False)
    settings = Gio.Settings.new_full(schema, None, None)
    return {key: settings.get_value(key).unpack() for key in schema.list_keys()}


def palette_for(style, definition=None):
    definition = definition or json.loads((ROOT / 'palette.json').read_text())
    palette = dict(definition['modes'].get(style.get('theme-mode'), definition['modes']['dark']))
    for key, token in [('accent-color', 'accent'), ('surface-color', 'background'), ('border-color', 'border')]:
        value = style.get(key, '')
        if COLOR.fullmatch(value):
            palette[token] = value
    return palette


def terminal_colors(style, definition=None):
    """Background, foreground, cursor and 16 ANSI colors for the current theme mode and family."""
    definition = definition or json.loads((ROOT / 'palette.json').read_text())
    palette = palette_for(style, definition)
    light = style.get('theme-mode') == 'light'
    mode = 'light' if light else 'dark'
    surface = str(style.get('surface-color', '')).upper()
    family = next((v[mode] for v in definition.get('families', {}).values()
                   if v[mode]['surface'].upper() == surface), None)
    if family:
        # A theme family supplies its own text and ANSI colors.
        return {'background': palette['background'], 'foreground': family['foreground'],
                'cursor': family['foreground'], 'ansi': list(family['ansi'])}
    ansi = list(definition['ansi-light' if light else 'ansi'])
    ansi[1] = palette['accent']  # default theme: red follows the accent
    return {'background': palette['background'], 'foreground': palette['foreground'],
            'cursor': palette['foreground'], 'ansi': ansi}


def render_css(css, style, definition=None):
    definition = definition or json.loads((ROOT / 'palette.json').read_text())
    palette = palette_for(style, definition)
    baseline = definition['modes']['dark']
    replacements = {value.upper(): palette[token] for token, value in baseline.items()}
    css = re.sub(r'#[0-9a-fA-F]{6}\b', lambda m: replacements.get(m[0].upper(), m[0]), css)
    font = style.get('clock-font', 'Doto')
    if font not in ('Doto', 'Space Mono', 'Space Grotesk'):
        font = 'Doto'
    ui_font = style.get('ui-font', 'Space Grotesk')
    if ui_font not in ('Space Grotesk', 'Space Mono', 'Sans'):
        ui_font = 'Space Grotesk'
    css = css.replace('font-family: "Space Grotesk"', f'font-family: "{ui_font}"')
    css = css.replace('font-family: "Doto"', f'font-family: "{font}"')
    radius = max(0, min(32, int(style.get('corner-radius', 8))))
    def corners(match):
        return 'border-radius: ' + re.sub(r'\d+(?:\.\d+)?px',
            lambda n: f'{radius if float(n[0][:-2]) else 0}px', match[1])
    css = re.sub(r'border-radius:\s*([^;{}]+)', corners, css)
    # Explicit titlebar corners must track the decoration radius too. Preserve
    # zero-valued maximized/tiled edges and joined control seams.
    css = re.sub(r'(border-(?:top|bottom)-(?:left|right)-radius:\s*)([1-9]\d*(?:\.\d+)?)px',
                 lambda match: f'{match[1]}{radius}px', css)
    outline = max(0, min(3, int(style.get('outline-width', 1))))
    css = re.sub(r'((?<![\w-])border(?:-(?:top|right|bottom|left))?:\s*)1px',
                 lambda match: f'{match[1]}{outline}px', css)
    css = re.sub(r'(box-shadow:\s*0 0 0 )1px', lambda match: f'{match[1]}{outline}px', css)
    return css


def application_css(style):
    shared = (ROOT / 'vendor/gtk.css').read_text()
    shared += f'\nwindow, dialog, popover, menu {{ font-size: {max(9, min(18, int(style.get("app-font-size", 11))))}pt; }}\n'
    palette = palette_for(style)
    gtk3 = render_css(shared, style)
    gtk4 = render_css(shared + '\n' + (ROOT / 'vendor/gtk4.css').read_text(), style)
    contrast = contrast_text(palette['accent'])
    selection_colors = (f'\n@define-color accent_fg_color {contrast};\n'
                        f'textview text selection, entry selection, check:checked, radio:checked {{ color: {contrast}; }}\n')
    gtk3 += selection_colors
    gtk4 += selection_colors
    gtk3 += scrollbar_css(style)
    gtk4 += scrollbar_css(style)
    if style.get('selection-style') == 'filled':
        selected = f'\nrow:selected, .view:selected, listview row:selected, gridview child:selected {{ background: {palette["accent"]}; color: {contrast_text(palette["accent"])}; }}\n'
        gtk3 += selected
        gtk4 += selected
        # App-specific Nautilus selectors must not override the selection control.
        gtk4 += f'\n.nautilus-list-view columnview > listview > row:selected, .nautilus-grid-view gridview > child:selected {{ background: {palette["accent"]}; color: {contrast_text(palette["accent"])}; }}\n'
    return gtk3 + DESKTOP_TRANSPARENCY, gtk4 + DESKTOP_TRANSPARENCY


def scrollbar_css(style):
    palette = palette_for(style)
    width = max(2, min(10, int(style.get('scrollbar-width', 4))))
    opacity = max(.35, min(1., float(style.get('scrollbar-opacity', .6))))
    color = palette['foreground'] if style.get('scrollbar-style') == 'monochrome' else palette['accent']
    radius = min(width / 2, max(0, int(style.get('corner-radius', 8))))
    return f'''
/* Narrow, transparent scrollbars. No filled gray gutters or padded handles. */
scrollbar, scrollbar contents, scrollbar trough {{ background: transparent; border: none; box-shadow: none; padding: 0; }}
scrollbar slider, scrollbar.overlay-indicator slider,
scrollbar.overlay-indicator:not(.dragging):not(.hovering) slider {{
    background: alpha({color}, {opacity}); border: none; box-shadow: none;
    border-radius: {radius:g}px; margin: 0;
}}
scrollbar.vertical, scrollbar.vertical:hover, scrollbar.vertical.overlay-indicator {{ min-width: {width}px; }}
scrollbar.horizontal, scrollbar.horizontal:hover, scrollbar.horizontal.overlay-indicator {{ min-height: {width}px; }}
scrollbar.vertical slider, scrollbar.vertical.overlay-indicator slider,
scrollbar.vertical.overlay-indicator:not(.dragging):not(.hovering) slider {{ min-width: {width}px; min-height: 24px; }}
scrollbar.horizontal slider, scrollbar.horizontal.overlay-indicator slider,
scrollbar.horizontal.overlay-indicator:not(.dragging):not(.hovering) slider {{ min-height: {width}px; min-width: 24px; }}
scrollbar slider:hover, scrollbar slider:active,
scrollbar.overlay-indicator slider:hover, scrollbar.overlay-indicator slider:active {{ background: {color}; }}
'''


def render_shell_css(style):
    palette = palette_for(style)
    width = max(2, min(10, int(style.get('scrollbar-width', 4))))
    opacity = max(.35, min(1., float(style.get('scrollbar-opacity', .6))))
    color = palette['foreground'] if style.get('scrollbar-style') == 'monochrome' else palette['accent']
    rgb = ','.join(str(int(color[i:i + 2], 16)) for i in (1, 3, 5))
    radius = min(width / 2, max(0, int(style.get('corner-radius', 8))))
    return render_css((ROOT / 'extension/stylesheet.css').read_text(), style) + f'''
.notheme-shell StScrollBar {{ padding: 0; }}
.notheme-shell StScrollView StScrollBar {{ min-width: {width}px; min-height: {width}px; }}
.notheme-shell StScrollBar StBin#trough {{ background-color: transparent; border: none; }}
.notheme-shell StScrollBar StButton#vhandle, .notheme-shell StScrollBar StButton#hhandle {{
    background-color: rgba({rgb},{opacity:g}); border: none; border-radius: {radius:g}px;
}}
.notheme-shell StScrollBar StButton#vhandle:hover, .notheme-shell StScrollBar StButton#hhandle:hover,
.notheme-shell StScrollBar StButton#vhandle:active, .notheme-shell StScrollBar StButton#hhandle:active {{ background-color: {color}; }}
'''


def contrast_text(hex_color):
    channels = [int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in channels]
    luminance = sum(a * b for a, b in zip(linear, (.2126, .7152, .0722)))
    return '#000000' if luminance > .179 else '#FFFFFF'


def wallpaper_svg(style):
    p = palette_for(style)
    dots = []
    for y in range(24, 1080, 32):
        for x in range(24, 1920, 32):
            r = 1.0
            dots.append(f'<circle cx="{x}" cy="{y}" r="{r:g}" fill="{p["border"]}"/>')
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080" viewBox="0 0 1920 1080">'
            f'<rect width="1920" height="1080" fill="{p["background"]}"/>' + ''.join(dots) + '</svg>')


def wallpaper_settings(style):
    background = palette_for(style)['background']
    return [('picture-options', 'zoom'), ('color-shading-type', 'solid'),
            ('primary-color', background), ('secondary-color', background)]


def update_terminals(tx, p, style, tmp):
    """Re-color terminals that were opted in with --apps (never opts new ones in)."""
    import re
    import notheme
    colors = terminal_colors(style)
    kitty = p['config'] / 'kitty/kitty.conf'
    if kitty.exists() and 'notheme: no fish dependency' in kitty.read_text():
        text = kitty.read_text()
        values = {'background': colors['background'], 'foreground': colors['foreground'],
                  'cursor': colors['cursor'], 'selection_background': colors['foreground'],
                  'selection_foreground': colors['background'],
                  **{f'color{i}': c for i, c in enumerate(colors['ansi'])}}
        for key, value in values.items():
            text = re.sub(rf'^{key} .*$', f'{key} {value}', text, flags=re.MULTILINE)
        source = tmp / 'kitty.conf'
        source.write_text(text)
        tx.install(source, kitty)
    try:
        profile = notheme.settings('org.gnome.Terminal.ProfilesList').get_string('default')
        path = f'/org/gnome/terminal/legacy/profiles:/:{profile}/'
        current = notheme.settings('org.gnome.Terminal.Legacy.Profile', path)
    except RuntimeError:
        return
    if not current.get_boolean('use-theme-colors') and current.get_string('font') == 'Space Mono 11':
        for key, value in [('background-color', colors['background']), ('foreground-color', colors['foreground']),
                           ('palette', colors['ansi'])]:
            tx.set('org.gnome.Terminal.Legacy.Profile', key, value, path)


def apply_application_style(follow_system=False):
    # Imports are delayed: build.py also imports this renderer.
    import fcntl
    import os
    import tempfile
    import notheme
    if os.geteuid() == 0:
        raise RuntimeError('Run as your desktop user, not root or sudo.')
    from icons import build_icons
    def write(path, content):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    style = read_style(ROOT / 'extension/schemas')
    if follow_system:
        scheme = notheme.settings('org.gnome.desktop.interface').get_string('color-scheme')
        style['theme-mode'] = 'dark' if scheme == 'prefer-dark' else 'light'
    gtk3, gtk4 = application_css(style)
    gtk3 = '@import url("file:///usr/share/themes/Yaru-dark/gtk-3.0/gtk.css");\n' + gtk3
    p = notheme.paths()
    theme = p['data'] / 'themes/notheme'
    if not (theme / 'gtk-3.0/gtk.css').exists():
        raise RuntimeError('Install notheme with ./notheme apply --yes first.')
    p['state'].mkdir(parents=True, exist_ok=True)
    with (p['state'] / 'lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        tx = notheme.Transaction(p['state'])
        print(f'Backup: {tx.directory}', flush=True)
        try:
            with tempfile.TemporaryDirectory(prefix='theme-', dir=p['state']) as tmp:
                for version, css in [('gtk-3.0', gtk3), ('gtk-4.0', gtk4)]:
                    source = Path(tmp) / version
                    source.write_text(css)
                    tx.install(source, theme / version / 'gtk.css')
                gtk3_user = p['config'] / 'gtk-3.0/gtk.css'
                gtk3_existing = gtk3_user.read_text() if gtk3_user.exists() else ''
                if '/* >>> notheme GTK3 >>> */' in gtk3_existing:
                    source = Path(tmp) / 'user-gtk3.css'
                    uri = (theme / 'gtk-3.0/gtk.css').as_uri()
                    source.write_text(notheme.gtk3_user_css(gtk3_existing, gtk3.partition('\n')[2], uri))
                    tx.install(source, gtk3_user)
                icons = Path(tmp) / 'icons'
                build_icons(icons, write, style.get('theme-mode', 'dark'))
                for icon in icons.rglob('*.svg'):
                    icon.write_text(render_css(icon.read_text(), style))
                tx.install(icons, p['data'] / 'icons/notheme')
                source = Path(tmp) / 'wallpaper.svg'
                source.write_text(wallpaper_svg(style))
                tx.install(source, p['data'] / 'backgrounds/notheme.svg')
                for mode in ('light', 'dark'):
                    source = Path(tmp) / f'wallpaper-{mode}.svg'
                    source.write_text(wallpaper_svg({**style, 'theme-mode': mode}))
                    target = p['data'] / f'backgrounds/notheme-{mode}.svg'
                    tx.install(source, target)
                    tx.set('org.gnome.desktop.background',
                           'picture-uri-dark' if mode == 'dark' else 'picture-uri', target.as_uri())
                # URI refresh alone retains old "centered" fitting and Ubuntu's
                # purple fallback. Own the fitting/fallback with the wallpaper.
                for key, value in wallpaper_settings(style):
                    tx.set('org.gnome.desktop.background', key, value)
                source = Path(tmp) / 'shell.css'
                shell_css = render_shell_css(style)
                source.write_text('@import url("file:///usr/share/themes/Yaru-dark/gnome-shell/gnome-shell.css");\n' +
                                  shell_css.replace('.notheme-shell {', 'stage {').replace('.notheme-shell ', ''))
                tx.install(source, theme / 'gnome-shell/gnome-shell.css')
                for asset in (ROOT / 'extension/assets').glob('*.svg'):
                    source = Path(tmp) / asset.name
                    source.write_text(render_css(asset.read_text(), style))
                    tx.install(source, theme / 'gnome-shell/assets' / asset.name)
                user_css = p['config'] / 'gtk-4.0/gtk.css'
                existing = user_css.read_text() if user_css.exists() else ''
                uri = (theme / 'gtk-4.0/gtk.css').as_uri()
                if '/* >>> notheme GTK4 >>> */' in existing or f'@import url("{uri}");' in existing:
                    source = Path(tmp) / 'user.css'
                    source.write_text(notheme.gtk4_user_css(existing, gtk4, uri))
                    tx.install(source, user_css)
                # A distinct GTK theme name emits a real theme change, making
                # running GTK apps reload CSS instead of retaining the old mode.
                # Icons follow the same rule. Rewriting files under an unchanged
                # icon-theme name is only picked up by lazy rescans, so icons
                # would lag the mode switch by seconds or until app restart.
                theme_name = 'notheme'
                if style['theme-mode'] == 'light':
                    theme_name = 'notheme-light'
                    tx.install(theme, p['data'] / 'themes' / theme_name)
                    tx.install(icons, p['data'] / 'icons' / theme_name)
                tx.set('org.gnome.desktop.interface', 'gtk-theme', theme_name)
                tx.set('org.gnome.desktop.interface', 'icon-theme', theme_name)
                if not follow_system:
                    tx.set('org.gnome.desktop.interface', 'color-scheme',
                           'prefer-light' if style['theme-mode'] == 'light' else 'prefer-dark')
                update_terminals(tx, p, style, Path(tmp))
                tx.manifest['status'] = 'applied'
                tx.save()
        except BaseException:
            notheme.restore_transaction(tx.directory, recovery=True)
            raise
    print('Application theme updated. Reopen apps. GTK4 overrides are updated only if already opted in.')


if __name__ == '__main__':
    try:
        import sys
        apply_application_style(follow_system='--follow-system' in sys.argv[1:])
    except Exception as error:
        raise SystemExit(str(error))
