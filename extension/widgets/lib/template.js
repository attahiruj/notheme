// A tiny template engine for widget.svg files. Pure string work, so it runs in the Shell,
// the preferences page and Node alike.
//
//   {{name}}              value, XML-escaped (numbers are rounded)
//   {{{name}}}            value inserted as-is (use for SVG fragments built in widget.js)
//   {{a.b}}               nested value; {{.}} is the current item inside {{#each}}
//   {{#if name}}..{{else}}..{{/if}}
//   {{#each list}}..{{/each}}   repeats with each item's fields in scope; outer values stay visible
const TOKEN = /\{\{\{\s*([^{}]+?)\s*\}\}\}|\{\{\s*([^{}]+?)\s*\}\}/g;
const cache = new Map();

function parse(source) {
    const stack = [{list: []}];
    let last = 0;
    const add = node => stack[stack.length - 1].list.push(node);
    for (const m of source.matchAll(TOKEN)) {
        if (m.index > last) add(source.slice(last, m.index));
        last = m.index + m[0].length;
        if (m[1]) { add({raw: m[1]}); continue; }
        const [tag, arg] = m[2].split(/\s+/, 2);
        if (tag === '#if') {
            const node = {kind: 'if', name: arg, yes: [], no: []};
            add(node);
            stack.push({node, list: node.yes});
        } else if (tag === '#each') {
            const node = {kind: 'each', name: arg, body: []};
            add(node);
            stack.push({node, list: node.body});
        } else if (tag === 'else') {
            const frame = stack[stack.length - 1];
            if (!frame.node || frame.node.kind !== 'if') throw new Error('widget template: {{else}} outside {{#if}}');
            frame.list = frame.node.no;
        } else if (tag === '/if' || tag === '/each') {
            if (stack.length < 2) throw new Error(`widget template: unmatched {{${tag}}}`);
            stack.pop();
        } else add({name: m[2]});
    }
    if (stack.length !== 1) throw new Error('widget template: unclosed block');
    if (last < source.length) add(source.slice(last));
    return stack[0].list;
}

function lookup(scopes, path) {
    if (path === '.') return scopes[scopes.length - 1];
    const [first, ...rest] = path.split('.');
    for (let i = scopes.length - 1; i >= 0; i--) {
        const scope = scopes[i];
        if (scope === null || typeof scope !== 'object' || !(first in scope)) continue;
        let value = scope[first];
        for (const key of rest) value = value?.[key];
        return value;
    }
    return undefined;
}

const text = value => {
    if (typeof value === 'number') return String(Math.round(value * 1000) / 1000);
    return String(value ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
};

function run(list, scopes) {
    let out = '';
    for (const node of list) {
        if (typeof node === 'string') out += node;
        else if (node.raw) out += lookup(scopes, node.raw) ?? '';
        else if (node.name && !node.kind) out += text(lookup(scopes, node.name));
        else if (node.kind === 'if') out += run(lookup(scopes, node.name) ? node.yes : node.no, scopes);
        else for (const item of lookup(scopes, node.name) ?? []) out += run(node.body, [...scopes, item]);
    }
    return out;
}

export function renderTemplate(source, values) {
    if (!cache.has(source)) cache.set(source, parse(source));
    return run(cache.get(source), [values]);
}
