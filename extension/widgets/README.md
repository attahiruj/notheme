# Widgets

Every widget is a self-contained folder: `widget.js` holds the logic and data mapping, and `widget.svg` holds the design. The SVG is optional: a widget whose drawing is mostly logic can build its SVG in JS instead (`chart.render`), and a text widget needs no drawing at all.

- `core/<id>/` – widgets that ship with notheme (maintained by the main developers)
- `user/<id>/` – widgets you create; shown under **Yours** in the settings widget browser
- `lib/`  – shared helpers (theme, grid layout, cairo drawing, formatting, mounting)
- `index.js` – registry; core widgets are listed there, user widgets via `user/index.js`

## Add a widget

```bash
./notheme widget new my-widget --name "My Widget" --category system --size 1x1 --author "Your Name"
./notheme settings          # preview it live
./notheme widget list       # core and user widgets
```

This creates `user/my-widget/` (`widget.js` and `widget.svg`) from a template and regenerates `user/index.js`.

`widget.js` exports `meta`, `build(sample, options)` (pure data, no toolkit calls) and, for a drawing, `chart`:

- **Template:** `chart = {size, vars(c)}` plus `widget.svg`. `vars` maps data to values; the SVG uses `{{name}}`, `{{{raw}}}`, `{{#if}}` and `{{#each}}`. Theme colors are always available as `{{fg}} {{dim}} {{line}} {{accent}} {{bg}} {{muted}}`, so widgets follow the user's colors.
- **Pure JS:** `chart = {size, render(c, w, h, theme)}` returns the SVG string; no `widget.svg`.

Import only from `../../lib/`, never from another widget. To contribute one upstream, move the folder to `core/` and list it in `index.js`.
