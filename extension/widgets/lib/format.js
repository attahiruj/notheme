// Small formatting helpers shared by widgets.
export const pad = value => String(value).padStart(2, '0');

export function formatBytes(bytes) {
    if (!Number.isFinite(bytes) || bytes < 0) return '—';
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    let value = bytes;
    let unit = 0;
    while (value >= 1000 && unit < units.length - 1) {
        value /= 1024;
        unit++;
    }
    return `${value < 10 && unit ? value.toFixed(1) : Math.round(value)} ${units[unit]}`;
}

export function formatDuration(seconds) {
    if (!Number.isFinite(seconds) || seconds < 0) return '—';
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor(seconds % 86400 / 3600);
    const minutes = Math.floor(seconds % 3600 / 60);
    return days ? `${days}D ${pad(hours)}H` : `${pad(hours)}:${pad(minutes)}`;
}

// Ten dots; the last lit dot takes the accent, like a Nothing glyph meter.
export function meter(fraction, total = 10) {
    const value = Number.isFinite(fraction) ? Math.min(1, Math.max(0, fraction)) : 0;
    const filled = Math.round(value * total);
    return {total, filled, current: filled - 1};
}

export const percent = fraction => Number.isFinite(fraction) ? `${Math.round(fraction * 100)}%` : '—';
// A card view: widgets return this from build().
export const card = (title, value, extra = {}) => ({kind: 'card', title, value, caption: '', ...extra});
