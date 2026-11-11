#!/usr/bin/python3
"""notheme: user-local installer with write-ahead backups and drift-aware restoration."""
import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import uuid

from build import ROOT, build
from theme import read_style, terminal_colors, wallpaper_settings
import legacy

UUID = 'notheme@local'
SHELL_VERSION = '50'
APPS = ['kitty', 'terminal', 'zsh', 'starship', 'btop', 'cava']


def paths():
    home = Path.home()
    return {
        'data': Path(os.environ.get('XDG_DATA_HOME', home / '.local/share')),
        'config': Path(os.environ.get('XDG_CONFIG_HOME', home / '.config')),
        'state': Path(os.environ.get('XDG_STATE_HOME', home / '.local/state')) / 'notheme',
    }


def digest(path):
    """Fingerprint links themselves; never follow an existing user's symlink."""
    if path.is_symlink():
        return 'link:' + os.readlink(path)
    if not path.exists():
        return None
    h = hashlib.sha256()
    if path.is_dir():
        for child in sorted(path.rglob('*')):
            h.update(str(child.relative_to(path)).encode())
            if child.is_symlink():
                h.update(('link:' + os.readlink(child)).encode())
            elif child.is_file():
                h.update(child.read_bytes())
    else:
        h.update(path.read_bytes())
    return h.hexdigest()


def remove(path):
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def copy(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.is_symlink():
        target.symlink_to(os.readlink(source))
    elif source.is_dir():
        shutil.copytree(source, target, symlinks=True)
    else:
        shutil.copy2(source, target)


def gio():
    try:
        from gi.repository import Gio, GLib
    except ImportError as error:
        raise RuntimeError('Install python3-gi (use the ./notheme wrapper).') from error
    return Gio, GLib


def settings(schema, path=None):
    Gio, _ = gio()
    source = Gio.SettingsSchemaSource.get_default()
    definition = source.lookup(schema, True)
    if not definition:
        raise RuntimeError(f'GSettings schema unavailable: {schema}')
    return Gio.Settings.new_full(definition, None, path)


class Transaction:
    def __init__(self, state):
        self.directory = state / 'backups' / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S') + '-' + uuid.uuid4().hex[:8])
        self.directory.mkdir(parents=True, mode=0o700)
        self.manifest = {'version': 1, 'status': 'applying', 'files': [], 'settings': []}
        self.save()

    def save(self):
        temporary = self.directory / 'manifest.tmp'
        temporary.write_text(json.dumps(self.manifest, indent=2) + '\n')
        temporary.replace(self.directory / 'manifest.json')

    def install(self, source, target):
        if digest(source) == digest(target):
            return
        original = digest(target)
        entry = {'path': str(target), 'before': original, 'after': digest(source), 'backup': None}
        if original is not None:
            entry['backup'] = f'files/{len(self.manifest["files"])}'
            copy(target, self.directory / entry['backup'])
        self.manifest['files'].append(entry)
        self.save()  # Record undo information before any destructive write.
        remove(target)
        copy(source, target)

    def set(self, schema, key, value, path=None):
        _, GLib = gio()
        obj = settings(schema, path)
        desired = GLib.Variant(obj.get_value(key).get_type_string(), value)
        if obj.get_value(key).equal(desired):
            return
        if not obj.is_writable(key):
            raise RuntimeError(f'Setting is locked by policy: {schema} {key}')
        before = obj.get_user_value(key)
        self.manifest['settings'].append({
            'schema': schema, 'key': key, 'path': path,
            'before': before.print_(True) if before is not None else None,
            'after': desired.print_(True),
        })
        self.save()
        if not obj.set_value(key, desired):
            raise RuntimeError(f'Failed setting {schema} {key}')
        gio()[0].Settings.sync()


def plan(args, out):
    p = paths()
    d, c = p['data'], p['config']
    files = [(out / 'fonts', d / 'fonts/notheme'),
             (out / 'theme', d / 'themes/notheme'),
             (out / 'icons', d / 'icons/notheme'),
             (out / 'cursors', d / f'icons/{BUNDLED_CURSOR}'),
             (out / 'wallpaper.svg', d / 'backgrounds/notheme.svg'),
             (out / 'extension', d / f'gnome-shell/extensions/{UUID}')]
    files.append((out / 'style-runtime', d / 'notheme/style-runtime'))
    for mode in ('light', 'dark'):
        files.append((out / f'wallpaper-{mode}.svg', d / f'backgrounds/notheme-{mode}.svg'))
    if args.libadwaita:
        files.append((out / 'gtk4-user.css', c / 'gtk-4.0/gtk.css'))
    if getattr(args, 'gtk3_overrides', False):
        files.append((out / 'gtk3-user.css', c / 'gtk-3.0/gtk.css'))
    for app in args.apps:
        for source, target in {
            'kitty': [('kitty.conf', 'kitty/kitty.conf')],
            'starship': [('starship.toml', 'starship.toml')],
            'btop': [('btop/themes/notheme.theme', 'btop/themes/notheme.theme'), ('btop.conf', 'btop/btop.conf')],
            'cava': [('cava/config', 'cava/config')],
            'terminal': [],
            'zsh': [('zsh-theme.zsh', 'notheme/zsh-theme.zsh')],
        }[app]:
            files.append((out / 'apps' / source, c / target))
    if 'zsh' in args.apps:
        files.append((out / 'zshrc', Path(os.environ.get('ZDOTDIR', Path.home())) / '.zshrc'))
    return files


def zsh_rc_content(existing, theme):
    import shlex
    existing = legacy.migrate_markers(existing, 'prompt')
    start, end = '# >>> notheme prompt >>>', '# <<< notheme prompt <<<'
    quoted = shlex.quote(str(theme))
    block = f'{start}\n[[ -r {quoted} ]] && source {quoted}\n{end}\n'
    if start in existing or end in existing:
        if existing.count(start) != 1 or existing.count(end) != 1 or existing.index(start) > existing.index(end):
            raise RuntimeError('Malformed notheme prompt block in .zshrc; no changes made.')
        begin, rest = existing.split(start, 1)
        _, tail = rest.split(end, 1)
        return begin + block.rstrip('\n') + tail
    return existing + ('\n' if existing and not existing.endswith('\n') else '') + block


def gtk4_user_css(existing, css, uri):
    return gtk_user_css(existing, css, uri, 'GTK4')


def gtk3_user_css(existing, css, uri):
    return gtk_user_css(existing, css, uri, 'GTK3')


def gtk_user_css(existing, css, uri, kind):
    """Keep user CSS, migrate our old early import, and manage only our block.

    Imported CSS came before stale user rules, so old colors silently won.
    Inline rules in a marked block avoid illegal late @imports and are reversible.
    """
    existing = legacy.migrate_markers(existing, kind)
    start, end = f'/* >>> notheme {kind} >>> */', f'/* <<< notheme {kind} <<< */'
    imports = (f'@import url("{uri}");', legacy.theme_import(uri))
    existing = ''.join(line for line in existing.splitlines(keepends=True) if line.strip() not in imports)
    block = f'{start}\n{css.rstrip()}\n{end}'
    if start in existing or end in existing:
        if existing.count(start) != 1 or existing.count(end) != 1 or existing.index(start) > existing.index(end):
            raise RuntimeError(f'Malformed notheme {kind} block; no changes made.')
        before, rest = existing.split(start, 1)
        _, after = rest.split(end, 1)
        return before + block + after
    return existing + ('\n' if existing and not existing.endswith('\n') else '') + block + '\n'


def desktop_settings(args):
    p = paths()
    style = read_style(ROOT / 'build/extension/schemas')
    values = [
        ('org.gnome.desktop.interface', 'color-scheme',
         'prefer-light' if style.get('theme-mode') == 'light' else 'prefer-dark'),
        ('org.gnome.desktop.interface', 'gtk-theme', 'notheme'),
        ('org.gnome.desktop.interface', 'icon-theme', 'notheme'),
        ('org.gnome.desktop.interface', 'font-name', 'Space Grotesk 11'),
        ('org.gnome.desktop.interface', 'document-font-name', 'Space Grotesk 11'),
        ('org.gnome.desktop.interface', 'monospace-font-name', 'Space Mono 11'),
        ('org.gnome.desktop.interface', 'clock-format', '24h'),
        ('org.gnome.desktop.wm.preferences', 'titlebar-font', 'Space Grotesk Medium 11'),
        ('org.gnome.desktop.wm.preferences', 'button-layout', ':minimize,maximize,close'),
        ('org.gnome.desktop.background', 'picture-uri', (p['data'] / 'backgrounds/notheme-light.svg').as_uri()),
        ('org.gnome.desktop.background', 'picture-uri-dark', (p['data'] / 'backgrounds/notheme-dark.svg').as_uri()),
    ]
    values += [('org.gnome.desktop.background', key, value) for key, value in wallpaper_settings(style)]
    if args.cursor and args.cursor != 'keep':
        values.append(('org.gnome.desktop.interface', 'cursor-theme', args.cursor))
        values.append(('org.gnome.desktop.interface', 'cursor-size', 24))
    if args.dock:
        values += [('org.gnome.shell.extensions.dash-to-dock', key, value) for key, value in [
            ('dock-position', 'LEFT'), ('extend-height', False), ('dash-max-icon-size', 36),
            ('transparency-mode', 'FIXED'), ('background-color', '#000000'), ('background-opacity', 1.0),
            ('custom-background-color', True), ('running-indicator-style', 'DOTS'),
        ]]
    return values


BUNDLED_CURSOR = 'notheme-cursor'  # built by tools/cursor.py and installed with the theme


def cursor_theme_exists(name):
    """Check Xcursor search locations, including themes inheriting real cursors."""
    import configparser
    if not name or Path(name).name != name or name in ('.', '..'):
        return False
    if name == BUNDLED_CURSOR:
        return True
    roots = [Path.home() / '.icons', paths()['data'] / 'icons']
    roots += [Path(p) / 'icons' for p in os.environ.get(
        'XDG_DATA_DIRS', '/usr/local/share:/usr/share').split(':') if p]
    roots += [Path(p).expanduser() for p in os.environ.get('XCURSOR_PATH', '').split(':') if p]
    seen = set()

    def find(theme):
        if theme in seen or Path(theme).name != theme or theme in ('.', '..'):
            return False
        seen.add(theme)
        for root in roots:
            directory = root / theme
            if any((directory / 'cursors' / pointer).is_file()
                   for pointer in ('left_ptr', 'default', 'arrow')):
                return True
            index = configparser.ConfigParser(interpolation=None)
            try:
                index.read(directory / 'index.theme')
                inherited = index.get('Icon Theme', 'Inherits', fallback='')
            except (configparser.Error, OSError):
                continue
            if any(find(parent.strip()) for parent in inherited.split(',') if parent.strip()):
                return True
        return False

    return find(name)


def extension_updates(enabled, disabled, enable=False):
    if not enable:
        return []
    if legacy.UUID in enabled and legacy.UUID not in disabled:
        raise RuntimeError('Disable the previous extension before enabling notheme; do not run both versions.')
    changes = []
    if UUID not in enabled:
        changes.append(('enabled-extensions', [*enabled, UUID]))
    if UUID in disabled:
        changes.append(('disabled-extensions', [item for item in disabled if item != UUID]))
    return changes


def preflight(args):
    if os.geteuid() == 0:
        raise RuntimeError('Run as your desktop user, not root or sudo.')
    if not all(Path('/usr/share/themes/Yaru-dark/gtk-3.0', name).exists() for name in ('gtk.css', 'gtk.gresource')):
        raise RuntimeError('Ubuntu Yaru base missing: sudo apt install yaru-theme-gtk')
    shell = subprocess.check_output(['gnome-shell', '--version'], text=True).strip()
    if shell.split()[-1].split('.')[0] != SHELL_VERSION:
        raise RuntimeError(f'This project targets GNOME {SHELL_VERSION}; found {shell}. No desktop changes made.')
    if args.cursor and args.cursor != 'keep' and not cursor_theme_exists(args.cursor):
        raise RuntimeError(f'Cursor theme {args.cursor!r} is not installed. Select '
                           'an installed theme with --cursor NAME, or --cursor keep.')
    if getattr(args, 'enable_extension', False):
        shell_settings = settings('org.gnome.shell')
        extension_updates(shell_settings.get_strv('enabled-extensions'),
                          shell_settings.get_strv('disabled-extensions'), True)
    # Resolve every schema/key and validate variants before making any changes.
    for schema, key, value in desktop_settings(args):
        obj = settings(schema)
        variant = gio()[1].Variant(obj.get_value(key).get_type_string(), value)
        if not obj.props.settings_schema.get_key(key).range_check(variant):
            raise RuntimeError(f'Unsupported setting: {schema} {key} = {value}')


def expand_apply_options(args):
    """--all opts into supported appearance assets, not extension activation."""
    if getattr(args, 'all', False):
        args.dock = True
        args.libadwaita = True
        args.gtk3_overrides = True
        args.apps = list(dict.fromkeys([*args.apps, *APPS]))
    return args


def apply(args):
    args = expand_apply_options(args)
    out = build()
    files = plan(args, out)
    print('Files to install (existing targets will be backed up):')
    for _, target in files:
        print(f'  {target}')
    print('\nDesktop settings:')
    for schema, key, value in desktop_settings(args):
        print(f'  {schema} {key} = {value}')
    if args.apps:
        print('\nApp configurations: ' + ', '.join(args.apps))
        print('  Existing configurations are backed up; terminal profile colors/fonts are opt-in too.')
    if getattr(args, 'all', False):
        print('  --all selects supported user themes/configs only; no packages, GDM or PAM changes')
    if 'zsh' in args.apps and 'starship' in args.apps:
        print('  Native zsh prompt takes precedence; Starship config is installed but not initialized')
    if args.enable_extension:
        print(f'  Enable {UUID} (other extensions remain unchanged)')
    else:
        print('  Preserve extension enablement; use --enable-extension to explicitly enable notheme')
    if not args.yes:
        print('\nPreview only. Use apply --yes with the same options to install.')
        return
    preflight(args)
    for source, _ in files:
        if source.name not in ('gtk4-user.css', 'gtk3-user.css', 'zshrc') and not source.exists():
            raise RuntimeError(f'Missing build artifact: {source}')
    if 'zsh' in args.apps:
        target = Path(os.environ.get('ZDOTDIR', Path.home())) / '.zshrc'
        original = target.read_text() if target.exists() else ''
        (out / 'zshrc').write_text(zsh_rc_content(original, paths()['config'] / 'notheme/zsh-theme.zsh'))
    if args.libadwaita:
        target = paths()['config'] / 'gtk-4.0/gtk.css'
        existing = target.read_text() if target.exists() else ''
        uri = (paths()['data'] / 'themes/notheme/gtk-4.0/gtk.css').as_uri()
        css = (out / 'theme/gtk-4.0/gtk.css').read_text()
        (out / 'gtk4-user.css').write_text(gtk4_user_css(existing, css, uri))
    if args.gtk3_overrides:
        target = paths()['config'] / 'gtk-3.0/gtk.css'
        existing = target.read_text() if target.exists() else ''
        uri = (paths()['data'] / 'themes/notheme/gtk-3.0/gtk.css').as_uri()
        # User CSS needs overrides, not a late @import of Yaru's base stylesheet.
        css = (out / 'theme/gtk-3.0/gtk.css').read_text().partition('\n')[2]
        (out / 'gtk3-user.css').write_text(gtk3_user_css(existing, css, uri))
    # Preserve btop's unrelated preferences while selecting the installed theme.
    if 'btop' in args.apps:
        import re
        target = paths()['config'] / 'btop/btop.conf'
        original = target.read_text() if target.exists() else ''
        line = 'color_theme = "notheme"'
        content, count = re.subn(r'^\s*color_theme\s*=.*$', line, original, flags=re.MULTILINE)
        (out / 'apps/btop.conf').write_text(content if count else original + '\n' + line + '\n')
    tx = Transaction(paths()['state'])
    print(f'\nBackup: {tx.directory}')
    try:
        for source, target in files:
            tx.install(source, target)
        for schema, key, value in desktop_settings(args):
            tx.set(schema, key, value)
        if 'terminal' in args.apps:
            profile = settings('org.gnome.Terminal.ProfilesList').get_string('default')
            path = f'/org/gnome/terminal/legacy/profiles:/:{profile}/'
            colors = terminal_colors(read_style(out / 'extension/schemas'))
            for key, value in [('use-theme-colors', False), ('background-color', colors['background']),
                               ('foreground-color', colors['foreground']), ('palette', colors['ansi']),
                               ('use-system-font', False), ('font', 'Space Mono 11')]:
                tx.set('org.gnome.Terminal.Legacy.Profile', key, value, path)
        obj = settings('org.gnome.shell')
        for key, value in extension_updates(obj.get_strv('enabled-extensions'),
                                           obj.get_strv('disabled-extensions'), args.enable_extension):
            tx.set('org.gnome.shell', key, value)
        tx.manifest['status'] = 'applied'
        tx.save()
    except BaseException:
        print('Apply interrupted. Restoring this transaction…', file=sys.stderr)
        restore_transaction(tx.directory, force=False, recovery=True)
        raise
    subprocess.run(['fc-cache', '-f', str(paths()['data'] / 'fonts/notheme')], check=False)
    print('\nApplied. Log out and back in to load the new GNOME extension and fonts.')
    print('Customize: ./notheme settings')
    if 'starship' in args.apps:
        print('Starship theme installed; shell initialization is NOT modified.')


def restore_transaction(directory, force=False, recovery=False):
    manifest_path = directory / 'manifest.json'
    m = json.loads(manifest_path.read_text())
    conflicts = []
    for entry in reversed(m['settings']):
        if entry.get('restored'):
            continue
        obj = settings(entry['schema'], entry['path'])
        current = obj.get_user_value(entry['key'])
        current_text = current.print_(True) if current is not None else None
        # A failed write may have left the original value unchanged.
        if current_text != entry['before']:
            if current_text != entry['after'] and not force:
                conflicts.append(f"setting {entry['schema']} {entry['key']}")
                continue
            if entry['before'] is None:
                obj.reset(entry['key'])
            elif not obj.set_value(entry['key'], gio()[1].Variant.parse(None, entry['before'], None, None)):
                raise RuntimeError(f"Could not restore {entry['key']}")
        entry['restored'] = True
        manifest_path.write_text(json.dumps(m, indent=2) + '\n')
    gio()[0].Settings.sync()
    for entry in reversed(m['files']):
        if entry.get('restored'):
            continue
        target = Path(entry['path'])
        current = digest(target)
        if current != entry['before']:
            if current not in (entry['after'], None) and not force:
                conflicts.append(str(target))
                continue
            remove(target)
            if entry['backup']:
                copy(directory / entry['backup'], target)
        entry['restored'] = True
        manifest_path.write_text(json.dumps(m, indent=2) + '\n')
    m['status'] = 'restore-conflicts' if conflicts else 'rolled-back' if recovery else 'restored'
    manifest_path.write_text(json.dumps(m, indent=2) + '\n')
    if conflicts:
        print('Preserved changes made since install; resolve these and retry restore:')
        for conflict in conflicts:
            print('  ' + conflict)
        print('Use restore --force only to deliberately discard those later changes.')
        return False
    print(f'Restored {directory.name}. Log out and back in to unload extension code.')
    return True


def backup_roots():
    state = paths()['state']
    return [state / 'backups', state.parent / legacy.NAMESPACE / 'backups']


def backup_manifests():
    return sorted((manifest for root in backup_roots() for manifest in root.glob('*/manifest.json')),
                  key=lambda manifest: (manifest.stat().st_mtime_ns, manifest.parent.name), reverse=True)


def restore(args):
    candidates = backup_manifests()
    if args.backup:
        # Only allow IDs from this installer's backup directory.
        if Path(args.backup).name != args.backup:
            raise RuntimeError('--backup expects a backup ID, not a path.')
        matches = [manifest.parent for manifest in candidates if manifest.parent.name == args.backup]
        if len(matches) != 1:
            raise RuntimeError('Backup ID is missing or ambiguous across the current and legacy backup stores.')
        directory = matches[0]
    else:
        candidate = next((p for p in candidates if json.loads(p.read_text())['status'] not in ('restored', 'rolled-back')), None)
        if candidate is None:
            raise RuntimeError('No active backup to restore.')
        directory = candidate.parent
    if not restore_transaction(directory, args.force):
        raise RuntimeError('Restore incomplete: later edits were preserved.')


def doctor():
    print('notheme / diagnostics (read-only)')
    for command in [['gnome-shell', '--version'], ['gsettings', 'get', 'org.gnome.desktop.interface', 'gtk-theme'],
                    ['gsettings', 'get', 'org.gnome.desktop.interface', 'icon-theme'],
                    ['gsettings', 'get', 'org.gnome.desktop.interface', 'cursor-theme'],
                    ['gsettings', 'get', 'org.gnome.desktop.interface', 'cursor-size'],
                    ['gnome-extensions', 'info', UUID]]:
        print('\n$ ' + ' '.join(command), flush=True)
        try:
            subprocess.run(command, check=False)
        except FileNotFoundError:
            print('Not installed: ' + command[0])
    print(f'\nSession: {os.environ.get("XDG_CURRENT_DESKTOP", "unknown")} / {os.environ.get("XDG_SESSION_TYPE", "unknown")}')
    for name, location in paths().items():
        print(f'{name}: {location}')
    print('\nBackups:')
    for manifest in backup_manifests():
        print(f'  {manifest.parent.name}: {json.loads(manifest.read_text())["status"]} ({manifest.parent.parent})')


def main():
    parser = argparse.ArgumentParser(prog='notheme', description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('build', help='Build assets locally; no desktop changes')
    sub.add_parser('doctor', help='Read-only environment and backup diagnostics')
    ap = sub.add_parser('apply', help='Preview, or install with --yes')
    ap.add_argument('--yes', action='store_true', help='Actually change the current user desktop')
    ap.add_argument('--all', action='store_true',
                    help='Select dock, GTK3/GTK4 overrides and every supported app config; enabling the extension is separate')
    ap.add_argument('--enable-extension', action='store_true',
                    help='Explicitly enable notheme; default preserves extension enablement')
    ap.add_argument('--apps', nargs='+', choices=APPS, default=[], help='Opt-in application configs (existing files backed up)')
    ap.add_argument('--libadwaita', action='store_true', help='Opt-in GTK4 global CSS; may break app styling')
    ap.add_argument('--gtk3-overrides', action='store_true',
                    help='Opt-in managed GTK3 user CSS to override stale custom dialog/button rules')
    ap.add_argument('--dock', action='store_true', help='Restyle Ubuntu Dock; does not enable/replace extensions')
    ap.add_argument('--cursor', default=BUNDLED_CURSOR,
                    help='Installed cursor theme at 24px (default: notheme-cursor, bundled); use keep to leave unchanged')
    sp = sub.add_parser('settings', help='Open the settings page: every option and the desktop widgets')
    sp.add_argument('--port', type=int, default=8765, help='Local port (default: 8765)')
    wp = sub.add_parser('widget', help='Developer tool: scaffold a widget (new), list them, or re-register (sync)')
    wp.add_argument('action', choices=['new', 'list', 'sync'])
    wp.add_argument('id', nargs='?', help='New widget id, e.g. battery-bars')
    wp.add_argument('--name', help='Display name')
    wp.add_argument('--author', help='Author shown in meta (default: git user.name)')
    wp.add_argument('--category', default='system', choices=['time', 'system', 'progress'])
    wp.add_argument('--size', default='1x1', choices=['1x1', '1x2', '2x1', '2x2', '3x1'])
    rp = sub.add_parser('restore', help='Restore latest active backup (newest first)')
    rp.add_argument('--backup', help='Specific backup ID shown by doctor')
    rp.add_argument('--force', action='store_true', help='Discard later edits to installer-managed targets')
    args = parser.parse_args()
    if args.command == 'build':
        print(build())
    elif args.command == 'doctor':
        doctor()
    elif args.command == 'widget':
        import widgets
        if args.action == 'new' and not args.id:
            parser.error('widget new needs an id')
        try:
            widgets.run(args)
        except ValueError as err:
            sys.exit(f'notheme: {err}')
    elif args.command == 'settings':
        import settings
        settings.serve(args.port)
    else:
        state = paths()['state']
        # Preview must not create state files or lock files outside the project.
        if args.command == 'apply' and not args.yes:
            apply(args)
            return
        state.mkdir(parents=True, exist_ok=True)
        with (state / 'lock').open('w') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            if args.command == 'apply':
                apply(args)
            else:
                restore(args)


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, OSError, subprocess.CalledProcessError) as error:
        print(f'Error: {error}', file=sys.stderr)
        sys.exit(1)
