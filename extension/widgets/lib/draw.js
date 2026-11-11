// Cairo drawing primitives. Pure cairo calls, so the Shell (St.DrawingArea) and
// preferences (Gtk.DrawingArea) share one renderer. Colors come from THEME.
import {THEME} from './theme.js';

export const TAU = Math.PI * 2;
export const ink = (cr, color, alpha = 1) => {
    const hex = /^#[0-9a-f]{6}$/i.test(color) ? color : THEME.fg;
    cr.setSourceRGBA(parseInt(hex.slice(1, 3), 16) / 255, parseInt(hex.slice(3, 5), 16) / 255,
        parseInt(hex.slice(5, 7), 16) / 255, alpha);
};
export const dot = (cr, x, y, r) => {
    if (THEME.square) cr.rectangle(x - r, y - r, r * 2, r * 2);
    else { cr.newSubPath(); cr.arc(x, y, r, 0, TAU); }
    cr.fill();
};
export const centered = (cr, str, x, y, size, color, family = THEME.font) => {
    cr.selectFontFace(family, 0, 1);
    cr.setFontSize(size);
    const e = cr.textExtents(str);
    ink(cr, color);
    cr.moveTo(x - e.width / 2 - e.xBearing, y - e.height / 2 - e.yBearing);
    cr.showText(str);
};
export const clamp01 = v => Number.isFinite(v) ? Math.min(1, Math.max(0, v)) : 0;
export const circle = (cr, x, y, r) => { cr.newSubPath(); cr.arc(x, y, r, 0, TAU); };
export const roundRect = (cr, x, y, w, h, r) => {
    r = THEME.square ? 0 : Math.min(r, w / 2, h / 2);
    cr.newSubPath();
    cr.arc(x + w - r, y + r, r, -TAU / 4, 0);
    cr.arc(x + w - r, y + h - r, r, 0, TAU / 4);
    cr.arc(x + r, y + h - r, r, TAU / 4, TAU / 2);
    cr.arc(x + r, y + r, r, TAU / 2, TAU * 0.75);
    cr.closePath();
};
