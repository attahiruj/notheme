"""Build self-contained desktop assets, without touching the user's desktop."""
import json
from pathlib import Path
import shutil
import subprocess
from icons import build_icons
from cursor import build_cursors
from theme import read_style, render_css, application_css, wallpaper_svg, render_shell_css

ROOT = Path(__file__).resolve().parents[1]


def write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def build():
    out = ROOT / 'build'
    p = json.loads((ROOT / 'palette.json').read_text())
    vendor = ROOT / 'vendor'
    if not (vendor / 'fonts/OFL.txt').exists():
        raise RuntimeError('Missing vendored fonts; see THIRD_PARTY.md.')
    shutil.copytree(vendor / 'fonts', out / 'fonts', dirs_exist_ok=True)
    shutil.copytree(ROOT / 'extension', out / 'extension', dirs_exist_ok=True)
    subprocess.run(['glib-compile-schemas', '--strict', str(out / 'extension/schemas')], check=True)
    style = read_style(out / 'extension/schemas')
    shutil.copy2(ROOT / 'palette.json', out / 'extension/palette.json')

    # Yaru is supplied by Ubuntu. Imports preserve its assets, states and accessibility.
    theme = out / 'theme'
    gtk3, gtk4 = application_css(style)
    write(theme / 'gtk-3.0/gtk.css', '@import url("file:///usr/share/themes/Yaru-dark/gtk-3.0/gtk.css");\n' + gtk3)
    write(theme / 'gtk-3.0/gtk-dark.css', '@import url("gtk.css");\n')
    # GTK registers gtk.gresource from the selected theme directory. Importing
    # another theme's CSS alone does NOT register that theme's resource bundle.
    resource = theme / 'gtk-3.0/gtk.gresource'
    if not resource.is_symlink() and resource.exists():
        raise RuntimeError(f'Unexpected file at {resource}; refusing to replace it.')
    if not resource.is_symlink():
        resource.symlink_to('/usr/share/themes/Yaru-dark/gtk-3.0/gtk.gresource')
    # GTK4 supplies its own base. This file is only imported with --libadwaita.
    write(theme / 'gtk-4.0/gtk.css', gtk4)
    write(out / 'login/notheme-login.css', render_css((vendor / 'login.css').read_text(), style))
    # User Themes discovers themes by this exact directory/file layout.
    # Use a known Ubuntu base, not whatever theme the user previously selected.
    # The standalone version cannot depend on the extension's uiGroup class.
    shell_css = render_shell_css(style)
    shell_css = shell_css.replace('/* Scoped to our stage class; disabling the extension restores the stock shell. */',
                                  '/* Standalone notheme shell theme for User Themes. */')
    write(theme / 'gnome-shell/gnome-shell.css',
          '@import url("file:///usr/share/themes/Yaru-dark/gnome-shell/gnome-shell.css");\n'
          + shell_css.replace('.notheme-shell {', 'stage {').replace('.notheme-shell ', ''))
    shutil.copytree(ROOT / 'extension/assets', theme / 'gnome-shell/assets', dirs_exist_ok=True)
    for asset in (theme / 'gnome-shell/assets').glob('*.svg'):
        asset.write_text(render_css(asset.read_text(), style))
    write(theme / 'index.theme', '[Desktop Entry]\nType=X-GNOME-Metatheme\nName=notheme\n'
          '[X-GNOME-Metatheme]\nGtkTheme=notheme\nIconTheme=notheme\nCursorTheme=notheme-cursor\n')

    def write_bytes(path, data):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    build_cursors(out / 'cursors', write_bytes, p['modes']['dark']['accent'])

    icons = out / 'icons'
    build_icons(icons, write, style.get('theme-mode', 'dark'))
    for icon in icons.rglob('*.svg'):
        icon.write_text(render_css(icon.read_text(), style))

    # Portable renderer for the preferences Apply button; no checkout dependency.
    runtime = out / 'style-runtime'
    for name in ('notheme.py', 'build.py', 'icons.py', 'cursor.py', 'theme.py', 'legacy.py'):
        write(runtime / 'tools' / name, (ROOT / 'tools' / name).read_text())
    for name in ('gtk.css', 'gtk4.css'):
        write(runtime / 'vendor' / name, (vendor / name).read_text())
    shutil.copy2(ROOT / 'palette.json', runtime / 'palette.json')
    shutil.copytree(out / 'extension/schemas', runtime / 'extension/schemas', dirs_exist_ok=True)
    shutil.copy2(ROOT / 'extension/stylesheet.css', runtime / 'extension/stylesheet.css')
    shutil.copytree(ROOT / 'extension/assets', runtime / 'extension/assets', dirs_exist_ok=True)

    # Static background only: clock and stats are live GNOME actors, not baked in.
    write(out / 'wallpaper.svg', wallpaper_svg(style))
    for mode in ('light', 'dark'):
        write(out / f'wallpaper-{mode}.svg', wallpaper_svg({**style, 'theme-mode': mode}))

    apps = out / 'apps'
    kitty = ['# notheme: no fish dependency or generated Quickshell includes.',
             'font_family Space Mono', 'bold_font Space Mono Bold', 'font_size 11',
             'background #000000', 'foreground #F2F2F2', 'cursor #F2F2F2',
             'selection_background #F2F2F2', 'selection_foreground #000000',
             'background_opacity 1', 'window_padding_width 18', 'cursor_shape block',
             'cursor_blink_interval 0', 'enable_audio_bell no']
    kitty += [f'color{i} {color}' for i, color in enumerate(p['ansi'])]
    write(apps / 'kitty.conf', '\n'.join(kitty) + '\n')
    shutil.copytree(vendor / 'apps', apps, dirs_exist_ok=True)
    write(apps / 'zsh-theme.zsh', render_css((vendor / 'apps/zsh-theme.zsh').read_text(), style))
    write(apps / 'btop.conf', 'color_theme = "notheme"\n')
    return out
