// Grid geometry: card shapes, how many cells fit, and card placement.
import {THEME} from './theme.js';

// Card shapes: columns x rows of grid units. Nothing else is allowed.
export const SHAPES = {'1x1': [1, 1], '1x2': [1, 2], '2x1': [2, 1], '2x2': [2, 2], '3x1': [3, 1]};

// Whole grid rows that fit in `height` pixels.
export const fitRows = height => Math.max(1, Math.floor((height + THEME.gap) / (THEME.unit + THEME.gap)));

// Grid units per row that fit in `width` pixels (at least two, so wide cards still fit).
export const fitColumns = width => Math.max(2, Math.floor((width + THEME.gap) / (THEME.unit + THEME.gap)));

// Placement of cards (shape names, in order) on a grid `columns` wide. `fixed[i]` is a {col, row}
// the user chose for card i (0-based) or null. Chosen cards go first, wherever they fit; the rest
// take the first free spot. A chosen spot that is off the grid or taken falls back to automatic.
// Returns {cells: [{col, row, cols, rows}], rows}.
export function packCards(shapes, columns, fixed = [], maxRows = Infinity) {
    const taken = [];
    const free = (col, row, cols, rows) => {
        for (let r = row; r < row + rows; r++)
            for (let c = col; c < col + cols; c++)
                if (taken[r]?.[c]) return false;
        return true;
    };
    const take = (col, row, cols, tall) => {
        for (let r = row; r < row + tall; r++) {
            taken[r] ??= [];
            for (let c = col; c < col + cols; c++) taken[r][c] = true;
        }
    };
    const size = name => {
        const [wide, tall] = SHAPES[name] ?? SHAPES['1x1'];
        return [Math.min(wide, columns), tall];
    };
    const cells = new Array(shapes.length).fill(null);
    shapes.forEach((name, i) => {
        const at = fixed[i];
        const [cols, tall] = size(name);
        if (!at || at.col < 0 || at.row < 0 || at.col + cols > columns || at.row + tall > maxRows || !free(at.col, at.row, cols, tall)) return;
        take(at.col, at.row, cols, tall);
        cells[i] = {col: at.col, row: at.row, cols, rows: tall};
    });
    shapes.forEach((name, i) => {
        if (cells[i]) return;
        const [cols, tall] = size(name);
        for (let row = 0; !cells[i]; row++) {
            for (let col = 0; col + cols <= columns; col++) {
                if (!free(col, row, cols, tall)) continue;
                take(col, row, cols, tall);
                cells[i] = {col, row, cols, rows: tall};
                break;
            }
        }
    });
    return {cells, rows: cells.reduce((max, c) => Math.max(max, c.row + c.rows), 0)};
}

// Drop `moved` at `at` ({col, row}) on a grid `columns` wide. `shapes` and `cells` describe every
// widget as it sits now (cells[i] = {col, row}, null for a widget not placed yet). Anything the dropped
// widget lands on is pushed to the nearest free cell. Returns the new {col, row} for every widget.
export function dropCard(shapes, columns, cells, moved, at, maxRows = Infinity) {
    const dims = shapes.map(name => {
        const [wide, tall] = SHAPES[name] ?? SHAPES['1x1'];
        return [Math.min(wide, columns), tall];
    });
    const out = cells.map(c => c && {col: c.col, row: c.row});
    out[moved] = {col: Math.max(0, Math.min(at.col, columns - dims[moved][0])), row: Math.max(0, Math.min(at.row, maxRows - dims[moved][1]))};
    const overlaps = (a, b) => a.col < b.col + dims[b.i][0] && b.col < a.col + dims[a.i][0]
        && a.row < b.row + dims[b.i][1] && b.row < a.row + dims[a.i][1];
    const box = i => ({...out[i], i});
    const pushed = [];
    out.forEach((c, i) => { if (c && i !== moved && overlaps(box(i), box(moved))) pushed.push(i); });
    const placed = new Set(out.map((c, i) => c && !pushed.includes(i) ? i : -1).filter(i => i >= 0));
    const free = (i, col, row) => ![...placed].some(j => overlaps({col, row, i}, box(j)));
    const rowLimit = out.reduce((max, c, i) => c ? Math.max(max, c.row + dims[i][1]) : max, 0) + 4;
    const todo = [...pushed, ...out.map((c, i) => c ? -1 : i).filter(i => i >= 0 && i !== moved)];
    for (const i of todo) {
        const from = out[i] ?? out[moved];
        let best = null;
        for (let row = 0; row < rowLimit; row++)
            for (let col = 0; col + dims[i][0] <= columns; col++) {
                if (!free(i, col, row)) continue;
                const d = Math.abs(col - from.col) + Math.abs(row - from.row);
                if (!best || d < best.d) best = {col, row, d};
            }
        out[i] = {col: best.col, row: best.row};
        placed.add(i);
    }
    return out;
}
