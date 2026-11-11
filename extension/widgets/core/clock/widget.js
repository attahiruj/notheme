// Dot clock widget. Self-contained: everything specific to it lives in this file.

export const meta = {id: 'clock', name: 'Dot clock', category: 'time', kind: 'text', size: '2x1', description: 'Large dot-matrix time in the clock font', author: 'Attahiru Jibril'};

const pad = value => String(value).padStart(2, '0');

export function clockText(hour, minute, second, twelve = false, seconds = false) {
    const h = twelve ? (hour % 12 || 12) : hour;
    return `${pad(h)}:${pad(minute)}${seconds ? `:${pad(second)}` : ''}${twelve ? (hour < 12 ? ' AM' : ' PM') : ''}`;
}

export function build(sample, options) {
    const time = sample.time;
    return {kind: 'clock', text: time
        ? clockText(time.hour, time.minute, time.second, options.twelve, options.seconds) : '--:--'};
}
