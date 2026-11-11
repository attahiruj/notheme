"""Compatibility identifiers only; never rename existing restore records or enable old code."""

NAMESPACE = 'glyph-ubuntu'
UUID = f'{NAMESPACE}@local'
THEME = 'Glyph-Nothing'


def migrate_markers(existing, kind):
    """Replace just an old managed block's delimiters, not unrelated user text."""
    if kind in ('GTK3', 'GTK4'):
        old = (f'/* >>> {NAMESPACE} {kind} >>> */', f'/* <<< {NAMESPACE} {kind} <<< */')
        new = (f'/* >>> notheme {kind} >>> */', f'/* <<< notheme {kind} <<< */')
    elif kind == 'prompt':
        old = (f'# >>> {NAMESPACE} prompt >>>', f'# <<< {NAMESPACE} prompt <<<')
        new = ('# >>> notheme prompt >>>', '# <<< notheme prompt <<<')
    else:
        raise ValueError('Unknown managed block kind')
    if not any(marker in existing for marker in old):
        return existing
    if (any(existing.count(marker) != 1 for marker in old) or
            existing.index(old[0]) > existing.index(old[1]) or
            any(marker in existing for marker in new)):
        raise RuntimeError('Conflicting or incomplete legacy managed blocks; no changes made.')
    return existing.replace(old[0], new[0], 1).replace(old[1], new[1], 1)


def theme_import(uri):
    return f'@import url("{uri.replace("/notheme/", f"/{THEME}/")}");'
