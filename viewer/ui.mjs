// Tiny DOM helpers + the Python/JS cross-check bookkeeping shared by every track panel.

export function h(tag, attrs, ...children) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === false || v === null || v === undefined) continue;
    if (k === 'class') el.className = v;
    else el.setAttribute(k, v === true ? '' : String(v));
  }
  for (const c of children.flat()) {
    if (c === null || c === undefined || c === false) continue;
    el.append(c instanceof Node ? c : document.createTextNode(String(c)));
  }
  return el;
}

/** Order-insensitive JSON for comparing Python and JS values. */
export function canon(v) {
  if (Array.isArray(v)) return `[${v.map(canon).join(',')}]`;
  if (v && typeof v === 'object') {
    return `{${Object.keys(v).sort().map((k) => `${JSON.stringify(k)}:${canon(v[k])}`).join(',')}}`;
  }
  return JSON.stringify(v === undefined ? null : v);
}

export const tf = (b) => (b === true ? 'T' : b === false ? 'F' : String(b));
export const words = (b) => (b === true ? 'true' : b === false ? 'false' : String(b));

/** Counts every Python-vs-JS comparison; each yields a visible, textual mark. */
export class CrossCheck {
  constructor() { this.agree = 0; this.disagree = 0; }
  mark(py, js) {
    const ok = canon(py) === canon(js);
    if (ok) this.agree += 1; else this.disagree += 1;
    return h('span', { class: `mark ${ok ? 'agree' : 'disagree'}`, 'data-agree': String(ok) },
      ok ? 'agree' : 'DISAGREE');
  }
}

/** Semantic table: caption, header cells with scope, optional row-header column. */
export function table(caption, headers, bodyRows, opts = {}) {
  const head = h('tr', {}, headers.map((x) => h('th', { scope: 'col' }, x)));
  const body = bodyRows.map((cells) => h('tr', {}, cells.map((c, i) =>
    (opts.rowHeader && i === 0) ? h('th', { scope: 'row' }, c) : h('td', {}, c))));
  return h('table', { class: opts.class || '' }, h('caption', {}, caption),
    h('thead', {}, head), h('tbody', {}, body));
}
