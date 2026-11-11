// Pure helpers: keep generated selectors scoped and sanitize all CSS inputs.
export const color = (value, fallback) => /^#[0-9a-f]{6}$/i.test(value) ? value : fallback;
export const number = (value, min, max, fallback) =>
    Number.isFinite(value) ? Math.min(max, Math.max(min, value)) : fallback;
export const clockFont = value => ['Doto', 'Space Mono', 'Space Grotesk'].includes(value) ? value : 'Doto';
export const uiFont = value => ['Space Grotesk', 'Space Mono', 'Sans'].includes(value) ? value : 'Space Grotesk';

// Relative luminance (0 black .. 1 white) of a #RRGGBB color.
export function luminance(hex) {
    const [r, g, b] = [1, 3, 5].map(i => parseInt(hex.slice(i, i + 2), 16) / 255)
        .map(c => c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4);
    return r * 0.2126 + g * 0.7152 + b * 0.0722;
}

// The mode palette with the user's colors on top. Text and outline tones follow the chosen
// surface: a light surface gets the light mode's ink, a dark one the dark mode's, so
// widgets and the shell stay readable whatever background is picked.
export function themePalette(definition, mode, overrides = {}) {
    const p = {...(definition.modes[mode] ?? definition.modes.dark)};
    const surface = color(overrides.surface, '');
    if (surface) {
        const ink = luminance(surface) > 0.4 ? definition.modes.light : definition.modes.dark;
        Object.assign(p, {foreground: ink.foreground, secondary: ink.secondary, muted: ink.muted, border: ink.border});
        p.background = surface;
    }
    p.accent = color(overrides.accent, p.accent);
    p.border = color(overrides.border, p.border);
    return p;
}

export function recolorCSS(css, definition, palette) {
    const replacements = Object.fromEntries(Object.entries(definition.modes.dark)
        .map(([token, value]) => [value.toUpperCase(), palette[token]]));
    return css.replace(/#[0-9a-f]{6}\b/gi, value => replacements[value.toUpperCase()] ?? value);
}

export function radiusCSS(css, value) {
    const radius = number(value, 0, 32, 8);
    // Include BoxPointer's -arrow-border-radius. Preserve deliberately square
    // joined edges, but update every nonzero corner in the shared template.
    return css.replace(/((?:-arrow-)?border-radius:\s*)([^;{}]+)/g, (_, property, corners) =>
        property + corners.replace(/\d+(?:\.\d+)?px/g, length => `${parseFloat(length) ? radius : 0}px`));
}

export function prioritizeCSS(css) {
    // St.Theme prepends newly loaded extension sheets. Equal-specificity rules
    // from an older sheet can therefore win. Repeating the first notheme class
    // adds specificity without changing which actors match (including desktop
    // actors outside uiGroup). Do not use !important or unscoped universal rules.
    return css.replace(/([^{}]+)\{/g, (_, selectors) => selectors.split(',')
        .map(selector => selector.replace(/\.(notheme-[\w-]+)/, '.$1.$1')).join(',') + '{');
}

export function toggleSVG(palette, active, radius = 8) {
    const border = active ? palette.accent : palette.border;
    const handle = active ? palette.accent : palette.secondary;
    const r = number(radius, 0, 32, 8);
    return `<svg xmlns="http://www.w3.org/2000/svg" width="44" height="24" viewBox="0 0 44 24"><rect x="0.5" y="0.5" width="43" height="23" rx="${Math.min(11.5, r)}" fill="${palette.background}" stroke="${border}"/><rect x="${active ? 25 : 5}" y="5" width="14" height="14" rx="${Math.min(7, r)}" fill="${handle}"/></svg>`;
}

export function styleCSS(v) {
    const a = color(v.accent, '#D71921');
    const b = color(v.surface, '#000000');
    const line = color(v.border, '#2A2A2A');
    const foreground = color(v.foreground, '#FFFFFF');
    const r = number(v.radius, 0, 32, 8);
    const font = clockFont(v.clockFont);
    const selected = v.selection === 'filled' ? a : b;
    // Pick readable text for bright as well as dark user-selected accents.
    const lum = luminance(a);
    const fg = v.selection === 'filled' ? (lum > 0.179 ? '#000000' : '#FFFFFF') : foreground;
    const scrollWidth = number(v.scrollbarWidth, 2, 10, 4);
    const scrollOpacity = number(v.scrollbarOpacity, 0.35, 1, 0.6);
    const scrollColor = v.scrollbarStyle === 'monochrome' ? foreground : a;
    const scrollRGB = [1, 3, 5].map(i => parseInt(scrollColor.slice(i, i + 2), 16));
    return `
.notheme-shell { font-family: "${uiFont(v.uiFont)}"; font-size: ${number(v.fontSize, 10, 18, 12)}pt; color: ${foreground}; }
.notheme-desktop { font-family: "${uiFont(v.uiFont)}"; }
.notheme-shell #panel .panel-button { -natural-hpadding: ${number(v.panelPadding, 4, 24, 12)}px; }
.notheme-shell #panel { height: ${number(v.panelHeight, 28, 56, 36)}px; background-color: ${b}; border-color: ${line}; }
.notheme-shell #panel .panel-button .system-status-icon { icon-size: ${number(v.panelIconSize, 12, 32, 16)}px; }
.notheme-shell #panel .clock-display .clock { font-family: "${font}"; font-size: ${number(v.panelClockSize, 14, 40, 24)}px; }
.notheme-shell .popup-menu-boxpointer, .notheme-shell .candidate-popup-boxpointer {
    -arrow-border-radius: ${r}px; -arrow-background-color: ${b}; -arrow-border-color: ${line}; }
.notheme-shell .popup-menu-content, .notheme-shell .quick-settings,
.notheme-shell .datemenu-popover, .notheme-shell .notification-banner,
.notheme-shell .calendar, .notheme-shell .message, .notheme-shell .quick-toggle-menu,
.notheme-shell .datemenu-today-button, .notheme-shell .events-button,
.notheme-shell .world-clocks-button, .notheme-shell .weather-button,
.notheme-shell .dash-background, .notheme-shell .modal-dialog,
.notheme-shell .osd-window, .notheme-shell .run-dialog,
.notheme-shell .search-entry, .notheme-shell .message-list-controls .button,
.notheme-card { background-color: ${b}; border-color: ${line}; border-radius: ${r}px; }
.notheme-shell .popup-menu-content, .notheme-shell .quick-settings,
.notheme-shell .datemenu-popover { padding: ${number(v.popupPadding, 6, 30, 12)}px; }
.notheme-shell .popup-menu-content, .notheme-shell .quick-settings,
.notheme-shell .calendar, .notheme-shell .message,
.notheme-shell .dash-background, .notheme-card { border-width: ${number(v.outlineWidth, 0, 3, 1)}px; }
.notheme-cards { spacing: ${number(v.widgetGap, 8, 48, 20)}px; }
.notheme-card { padding: ${number(v.cardPadding, 0, 15, 8)}px; }
.notheme-pip { border-radius: ${v.dotShape === 'square' ? 0 : 4}px; }
.notheme-shell .quick-toggle, .notheme-shell .quick-settings .button,
.notheme-shell .quick-settings .icon-button { background-color: ${b}; border-color: ${line}; border-radius: ${r}px; }
.notheme-shell .quick-toggle-has-menu,
.notheme-shell .quick-settings-system-item .icon-button,
.notheme-shell .calendar .calendar-day,
.notheme-shell .calendar .calendar-month-header .pager-button { border-radius: ${r}px; }
.notheme-shell .quick-toggle-has-menu .quick-toggle:ltr { border-radius: ${r}px 0 0 ${r}px; }
.notheme-shell .quick-toggle-has-menu .quick-toggle:rtl { border-radius: 0 ${r}px ${r}px 0; }
.notheme-shell .quick-toggle-has-menu .quick-toggle:ltr:last-child,
.notheme-shell .quick-toggle-has-menu .quick-toggle:rtl:last-child { border-radius: ${r}px; }
.notheme-shell .quick-toggle-has-menu .quick-toggle-menu-button { background-color: ${b}; border-color: ${line}; }
.notheme-shell .quick-toggle-has-menu .quick-toggle-menu-button:ltr { border-radius: 0 ${r}px ${r}px 0; }
.notheme-shell .quick-toggle-has-menu .quick-toggle-menu-button:rtl { border-radius: ${r}px 0 0 ${r}px; }
.notheme-shell .quick-settings .quick-toggle:checked,
.notheme-shell .quick-settings .quick-toggle:checked:hover,
.notheme-shell .quick-toggle-has-menu .quick-toggle-menu-button:checked,
.notheme-shell .quick-toggle-has-menu .quick-toggle-menu-button:checked:hover,
.notheme-shell .calendar .calendar-day.calendar-today,
.notheme-shell .calendar .calendar-day:selected {
    background-color: ${selected}; color: ${fg}; border-color: ${a}; }
.notheme-shell .quick-toggle:checked .quick-toggle-icon { color: ${v.selection === 'filled' ? fg : a}; }
.notheme-shell .quick-settings .button:focus, .notheme-shell .search-entry:focus { border-color: ${a}; }
.notheme-shell #panel .panel-button#panelActivities .workspace-dot:active, .notheme-shell #panel .panel-button#panelActivities .workspace-dot.active, .notheme-shell .quick-toggle-menu .header .icon.active { color: ${a}; }
.notheme-shell .app-grid-running-dot { background-color: ${a}; }
.notheme-shell .slider { -barlevel-active-background-color: ${a}; -barlevel-active-border-color: ${a}; }
.notheme-shell StScrollBar { padding: 0; }
.notheme-shell StScrollView StScrollBar { min-width: ${scrollWidth}px; min-height: ${scrollWidth}px; }
.notheme-shell StScrollBar StBin#trough { background-color: transparent; border: none; }
.notheme-shell StScrollBar StButton#vhandle,
.notheme-shell StScrollBar StButton#hhandle {
    background-color: rgba(${scrollRGB.join(',')},${scrollOpacity}); border: none;
    border-radius: ${Math.min(r, scrollWidth / 2)}px;
}
.notheme-shell StScrollBar StButton#vhandle:hover,
.notheme-shell StScrollBar StButton#hhandle:hover,
.notheme-shell StScrollBar StButton#vhandle:active,
.notheme-shell StScrollBar StButton#hhandle:active { background-color: ${scrollColor}; }
.notheme-desktop-clock, .notheme-card-value,
.notheme-shell .world-clocks-button .world-clocks-time { font-family: "${font}"; }
.notheme-lock .unlock-dialog, .notheme-lock .screen-shield-background { background-color: ${b}; }
.notheme-lock .screen-shield-background { opacity: 0; }
.notheme-lock .unlock-dialog-clock-time { font-family: "${font}"; font-size: ${number(v.lockClockSize, 48, 160, 96)}px; font-weight: 700; color: ${foreground}; }
.notheme-lock .unlock-dialog-clock-date { font-family: "Space Mono"; font-size: 18px; color: ${foreground}; }
.notheme-lock .unlock-dialog .login-dialog-prompt-layout { background-color: ${b}; border: 1px solid ${line}; border-radius: ${r}px; box-shadow: none; padding: 32px 36px; }
.notheme-lock .unlock-dialog .user-widget { margin-bottom: 8px; }
.notheme-lock .unlock-dialog .login-dialog-prompt-entry { background-color: ${b}; color: ${foreground}; border: 1px solid ${line}; border-radius: ${r}px; box-shadow: none; }
.notheme-lock .unlock-dialog .login-dialog-prompt-entry:focus { border-color: ${a}; box-shadow: none; }
.notheme-lock .unlock-dialog .user-widget-label,
.notheme-lock .unlock-dialog .login-dialog-message { color: ${foreground}; }
`;
}
