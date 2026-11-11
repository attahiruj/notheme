# Contributing

Thanks for helping. notheme changes a real desktop, so the main rule is: **be careful with the installer, and prove it with a test.**

## Setup

You need the packages from the README's Requirements section and GNOME Shell 50. Nothing else: the tools are plain Python 3 and the extension is plain GJS, with no build system or package manager.

```bash
./notheme build                          # render everything into build/, no desktop changes
python3 -m unittest discover -s tests    # installer and renderer tests
```

The tests set `GSETTINGS_BACKEND=memory` and use temporary directories, so they never touch your real settings or files. Keep it that way: a test must never write to your home directory or dconf.

`tests/style-smoke.js` parses the generated shell CSS with GNOME Shell's own parser. It needs a GJS environment with Shell libraries, so run it only if you changed the extension styles.

## Layout

| Path | What |
| --- | --- |
| `notheme` | Entry script |
| `tools/notheme.py` | CLI, transactions, backups and restore |
| `tools/build.py` | Renders all assets into `build/` |
| `tools/theme.py`, `icons.py`, `cursor.py` | CSS/wallpaper, pixel icons, pixel cursor generators |
| `tools/settings.py`, `settings.html` | Local settings server and page |
| `extension/` | GNOME Shell extension (`notheme@local`) and desktop widgets |
| `vendor/` | Bundled fonts and app configs; provenance in `THIRD_PARTY.md` |
| `palette.json` | Dark and light colors, ANSI palette |
| `build/` | Generated; git-ignored |

## Installer rules

- **Preview first.** Without `--yes`, nothing may change. New options follow the same rule.
- **Back up and be reversible.** Anything written to the user's system must be recorded in the transaction so `restore` can undo it, and must not clobber changes the user made afterwards.
- **No root, no downloads, no package installs, no login-shell changes.**
- **Opt-in for risky changes.** GTK4 overrides, dock settings and app configs stay behind flags.
- **Validate before changing.** Check schemas, keys and versions up front so a failure leaves the desktop untouched.
- Existing restore records and legacy `glyph-ubuntu` identifiers must keep working (`tools/legacy.py`); never rename them.

Add or update a test in `tests/test_installer.py` for any installer change.

## Assets

- **Icons and cursors** are generated from pixel sprites in code, not binary files. To change a cursor, edit its sprite in `tools/cursor.py`, run `./notheme build`, and look at the result on both dark and light backgrounds. Sprites are at most 10x10 cells; the outline is automatic.
- **Colors** come from `palette.json` and the user's settings. Don't hard-code hex values in CSS that should follow the theme.
- **Vendored files**: record where anything new came from, and its license, in `THIRD_PARTY.md`. Don't add assets whose license you can't redistribute under GPL-3.0.

## Widgets

```bash
./notheme widget new my-widget --name "My Widget" --category system --size 1x1
./notheme settings
```

See `extension/widgets/README.md`. Widgets that ship with notheme live in `extension/widgets/core/`.

## Testing on a real desktop

Run the installer only as your normal user, and keep the backup ID it prints. If something looks wrong, `./notheme restore` reverts the newest install, and the README's Restore section covers recovering an unstable shell. Don't restart GDM or run `gnome-shell --replace` in your active session.

## Pull requests

- Keep changes focused; describe what changed and how you tested it.
- Run the test suite and include screenshots for anything visual (dark and light).
- Match the surrounding style. Python is plain and standard-library only; please don't add dependencies.
- Contributions are licensed under GPL-3.0, the same as the project.
