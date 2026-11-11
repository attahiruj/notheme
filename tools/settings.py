"""notheme settings: a local web page that edits every notheme option and the desktop widgets.

Run with `./notheme settings`. The page serves the real widget code from extension/, reads
and writes the extension's GSettings keys, and the desktop updates live as you change things.
Nothing is reachable from other hosts or other web pages.
"""
import ast
import http.server
import json
import re
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE = '/tools/settings.html'
SCHEMA = 'org.gnome.shell.extensions.notheme'
SCHEMA_XML = ROOT / 'extension' / 'schemas' / f'{SCHEMA}.gschema.xml'
MAX_BODY = 64 * 1024
# Older versions stored one boolean per widget; the extension migrates them, the page never shows them.
LEGACY = {'show-date', 'show-greeting', 'show-stats', 'show-clock', 'show-cpu', 'show-memory'}
LIST_ENTRY = re.compile(r'[a-z][a-z0-9-]*(@\d{1,2},\d{1,2})?')
SCHEMA_DIR = None


def load_schema():
    """key -> {type, default, min, max, choices} straight from the schema file."""
    keys = {}
    for node in ET.parse(SCHEMA_XML).getroot().iter('key'):
        name = node.get('name')
        if name in LEGACY:
            continue
        default = node.findtext('default').strip()
        info = {'type': node.get('type'),
                'default': ast.literal_eval(default.replace('true', 'True').replace('false', 'False'))}
        rng = node.find('range')
        if rng is not None:
            info['min'], info['max'] = float(rng.get('min')), float(rng.get('max'))
        choices = [c.get('value') for c in node.iter('choice')]
        if choices:
            info['choices'] = choices
        keys[name] = info
    return keys


def compile_schemas():
    global SCHEMA_DIR
    SCHEMA_DIR = tempfile.mkdtemp(prefix='notheme-settings-schemas-')
    subprocess.run(['glib-compile-schemas', '--strict', '--targetdir', SCHEMA_DIR, str(SCHEMA_XML.parent)], check=True)


def gsettings(*args):
    return subprocess.run(['gsettings', '--schemadir', SCHEMA_DIR, *args], capture_output=True, text=True, timeout=10)


def read_state(keys):
    state = {}
    for key in keys:
        out = gsettings('get', SCHEMA, key)
        if out.returncode:
            continue
        text = re.sub(r'^@\w+ ', '', out.stdout.strip()).replace('true', 'True').replace('false', 'False')
        try:
            state[key] = ast.literal_eval(text)
        except (ValueError, SyntaxError):
            pass
    return state


def variant(keys, key, value):
    info = keys[key]
    kind = info['type']
    if kind == 'b' and isinstance(value, bool):
        return 'true' if value else 'false'
    if kind in 'id' and isinstance(value, (int, float)) and not isinstance(value, bool):
        if 'min' in info and not info['min'] <= value <= info['max']:
            raise ValueError(f'{key} is out of range')
        return str(int(value)) if kind == 'i' else repr(float(value))
    if kind == 's' and isinstance(value, str) and len(value) < 200:
        if 'choices' in info and value not in info['choices']:
            raise ValueError(f'bad value for {key}')
        return "'" + value.replace('\\', '\\\\').replace("'", "\\'") + "'"
    if kind == 'as' and isinstance(value, list) and len(value) < 64 and all(
            isinstance(v, str) and LIST_ENTRY.fullmatch(v) for v in value):
        return '[' + ', '.join(f"'{v}'" for v in value) + ']'
    raise ValueError(f'bad value for {key}')


def stamp():
    files = [*(ROOT / 'extension').rglob('*'), ROOT / 'tools' / 'settings.html', ROOT / 'palette.json']
    return max((f.stat().st_mtime_ns for f in files if f.is_file()), default=0)


def runtime_theme_script():
    """The installed renderer that restyles apps (the same one the installer ships)."""
    from os import environ
    base = Path(environ.get('XDG_DATA_HOME') or Path.home() / '.local/share')
    return base / 'notheme' / 'style-runtime' / 'tools' / 'theme.py'


class Handler(http.server.SimpleHTTPRequestHandler):
    port = 8765
    keys = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def _local(self):
        # Blocks DNS-rebinding: only our own origin may talk to the API.
        return self.headers.get('Host', '') in {f'localhost:{self.port}', f'127.0.0.1:{self.port}'}

    def _json(self, code, data):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split('?')[0]
        if not self._local():
            return self.send_error(403)
        if path == '/':
            self.send_response(302); self.send_header('Location', PAGE); self.end_headers(); return
        if path == '/__stamp':
            return self._json(200, stamp())
        if path == '/api/schema':
            return self._json(200, self.keys)
        if path == '/api/state':
            return self._json(200, read_state(self.keys))
        if not (path == PAGE or path == '/palette.json' or path.startswith('/extension/') and '..' not in path):
            return self.send_error(404)
        super().do_GET()

    def do_POST(self):
        # A custom header cannot be sent cross-site without a CORS preflight, which we never grant.
        if self.path not in ('/api/set', '/api/reset', '/api/apply-apps') or not self._local() \
                or self.headers.get('X-Notheme') != '1':
            return self.send_error(403)
        length = int(self.headers.get('Content-Length') or 0)
        if length > MAX_BODY:
            return self.send_error(413)
        if self.path == '/api/reset':
            result = gsettings('reset-recursively', SCHEMA)
            return self._json(200 if not result.returncode else 422,
                              {'ok': not result.returncode, 'error': result.stderr.strip()})
        if self.path == '/api/apply-apps':
            return self._apply_apps()
        try:
            changes = json.loads(self.rfile.read(length))
            if not isinstance(changes, dict) or not set(changes) <= set(self.keys):
                raise ValueError('unknown setting')
            values = {key: variant(self.keys, key, value) for key, value in changes.items()}
        except ValueError as error:
            return self._json(400, {'ok': False, 'error': str(error)})
        failed = {}
        for key, value in values.items():
            result = gsettings('set', SCHEMA, key, value)
            if result.returncode:
                failed[key] = result.stderr.strip()
        self._json(200 if not failed else 422, {'ok': not failed, 'written': len(values) - len(failed), 'failed': failed})

    def _apply_apps(self):
        script = runtime_theme_script()
        if not script.exists():
            return self._json(422, {'ok': False, 'error': 'Not installed yet. Run ./notheme apply --yes first.'})
        try:
            result = subprocess.run(['/usr/bin/python3', '-B', str(script)], capture_output=True, text=True, timeout=120)
        except (OSError, subprocess.TimeoutExpired) as error:
            return self._json(422, {'ok': False, 'error': str(error)})
        self._json(200 if not result.returncode else 422,
                   {'ok': not result.returncode, 'error': (result.stderr or result.stdout).strip()})

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')
        super().end_headers()

    def log_message(self, *args):
        pass


def serve(port=8765):
    Handler.port = port
    Handler.keys = load_schema()
    compile_schemas()
    server = http.server.ThreadingHTTPServer(('127.0.0.1', port), Handler)
    print(f'notheme settings: http://localhost:{port}   (Ctrl+C to stop)')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
