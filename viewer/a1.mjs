// Track A1 panel. Every "JS" value is RECOMPUTED here from formula structures only, using the independent
// viewer/parity/logic.mjs (truth tables, models, entails) plus three small kernels that module lacks
// (countermodel, strong-Kleene partial evaluation, proof checker). Python's values come from the packet.
import { toStr, variables, models, truthTable, entails } from './parity/logic.mjs';
import { h, table, tf, words, canon } from './ui.mjs';

// ---------- extra JS kernels (independent of Python) ----------
const and = (l, r) => ({ op: 'and', left: l, right: r });
const not = (o) => ({ op: 'not', operand: o });
const vr = (n) => ({ op: 'var', name: n });

function countermodelJS(premises, conclusion) {
  const names = [...new Set([...premises, conclusion].flatMap((f) => variables(f)))].sort();
  const goal = premises.reduce((acc, p) => and(acc, p), not(conclusion));
  const first = models(goal, names)[0];
  return first === undefined ? null : first;
}

function kleene(f, a) {
  const has = (n) => Object.prototype.hasOwnProperty.call(a, n);
  switch (f.op) {
    case 'const': return f.value;
    case 'var': return has(f.name) ? a[f.name] : null;
    case 'not': { const v = kleene(f.operand, a); return v === null ? null : !v; }
    default: {
      const l = kleene(f.left, a); const r = kleene(f.right, a);
      if (f.op === 'and') return (l === false || r === false) ? false : (l === null || r === null) ? null : true;
      if (f.op === 'or') return (l === true || r === true) ? true : (l === null || r === null) ? null : false;
      if (f.op === 'implies') {
        const nl = l === null ? null : !l;
        return (nl === true || r === true) ? true : (nl === null || r === null) ? null : false;
      }
      return (l === null || r === null) ? null : l === r; // iff
    }
  }
}

function partialJS(f, a) {
  const v = kleene(f, a);
  if (v === null) {
    const missing = variables(f).filter((n) => !Object.prototype.hasOwnProperty.call(a, n));
    return { status: 'unknown', value: null, reason: `unassigned: ${missing.sort().join(', ')}` };
  }
  return { status: 'known', value: v, reason: '' };
}

const ARITY = { premise: 0, modus_ponens: 2, modus_tollens: 2, and_intro: 2, and_elim_left: 1, and_elim_right: 1,
  or_intro_left: 1, or_intro_right: 1, double_negation_elim: 1 };

function checkProofJS(steps, premises) {
  const prem = premises.map(toStr); const seen = [];
  for (let i = 0; i < steps.length; i++) {
    const { formula, rule, cites } = steps[i];
    const bad = (d) => ({ ok: false, bad_step: i, reason: `step ${i} (${rule}): ${d}` });
    if (cites.length !== ARITY[rule]) return bad(`rule takes ${ARITY[rule]} cites, got ${cites.length}`);
    for (const c of cites) {
      if (!(Number.isInteger(c) && c >= 0 && c < i)) return bad(`cites step ${c}, which is not an earlier step`);
    }
    const f = formula; const c = cites.map((k) => seen[k]);
    let ok;
    switch (rule) {
      case 'premise': ok = prem.includes(toStr(f)); break;
      case 'modus_ponens': ok = c[0].op === 'implies' && toStr(c[1]) === toStr(c[0].left) && toStr(f) === toStr(c[0].right); break;
      case 'modus_tollens': ok = c[0].op === 'implies' && c[1].op === 'not' && toStr(c[1].operand) === toStr(c[0].right)
        && toStr(f) === toStr(not(c[0].left)); break;
      case 'and_intro': ok = toStr(f) === toStr(and(c[0], c[1])); break;
      case 'and_elim_left': ok = c[0].op === 'and' && toStr(f) === toStr(c[0].left); break;
      case 'and_elim_right': ok = c[0].op === 'and' && toStr(f) === toStr(c[0].right); break;
      case 'or_intro_left': ok = f.op === 'or' && toStr(f.left) === toStr(c[0]); break;
      case 'or_intro_right': ok = f.op === 'or' && toStr(f.right) === toStr(c[0]); break;
      case 'double_negation_elim': ok = c[0].op === 'not' && c[0].operand.op === 'not' && toStr(f) === toStr(c[0].operand.operand); break;
      default: return bad('unknown rule');
    }
    if (!ok) return bad('rule conditions not met');
    seen.push(f);
  }
  return { ok: true, bad_step: null, reason: '' };
}

const asg = (a) => Object.entries(a).map(([k, v]) => `${k}=${tf(v)}`).join(' ') || '(empty)';
const mono = (s) => h('code', {}, s);

// ---------- views ----------
export function views(packet, { xc }) {
  const P = packet.panels;
  return [truthTableView(P, xc), countermodelView(P, xc), wumpusView(P, xc), proofView(P, xc),
    partialView(P, xc), inductionView(P, xc)];
}

function truthTableView(P, xc) {
  const all = P.truth_tables;
  // Recompute everything for every formula; summary row per formula.
  const summary = all.map((c) => {
    const js = truthTable(c.structure);
    const rowsAgree = canon(js) === canon(c.rows);
    const jsModels = models(c.structure).length;
    const jsValid = js.every((r) => r.value);
    return [c.name, mono(c.string), String(c.rows.length), `${c.model_count} / ${jsModels}`,
      xc.mark([c.rows, c.model_count, c.satisfiable, c.valid, c.string],
        [js, jsModels, jsModels > 0, jsValid, toStr(c.structure)]),
      rowsAgree ? 'all rows agree' : 'rows differ'];
  });
  const sel = h('select', { id: 'tt-select' }, all.map((c) => h('option', { value: c.name }, `${c.name}  ${c.string}`)));
  const initial = all.find((c) => c.name === 'distribution') || all.find((c) => c.variables.length === 3) || all[0];
  sel.value = initial.name;
  const detail = h('div', { id: 'tt-detail' });
  const result = h('p', { class: 'text-result', id: 'tt-text', 'aria-live': 'polite' });
  function render() {
    const c = all.find((x) => x.name === sel.value);
    const js = truthTable(c.structure);
    const rows = c.rows.map((r, i) => [
      ...c.variables.map((n) => tf(r.assignment[n])), tf(r.value), tf(js[i].value), xc.mark(r.value, js[i].value)]);
    const t = table(`Truth table of ${c.string} (T = true, F = false; first variable changes slowest)`,
      [...(c.variables.length ? c.variables : []), 'Python value', 'JS value', 'Check'], rows);
    t.querySelectorAll('td').forEach((td) => td.classList.add('c'));
    detail.replaceChildren(t);
    const jsModels = models(c.structure).length;
    result.textContent = `${c.string} has ${c.rows.length} row(s) and ${c.model_count} model(s) in Python and ${jsModels} in JS; `
      + `satisfiable: ${words(c.satisfiable)}; valid: ${words(c.valid)}.`;
  }
  sel.addEventListener('change', render);
  render();
  const node = h('div', {},
    h('p', {}, h('label', { for: 'tt-select' }, 'Formula'), sel),
    result, detail,
    table('All fixture formulas, recomputed in JS (the mark compares strings, tables, model count, satisfiable, valid)',
      ['Name', 'Formula', 'Rows', 'Models (Py / JS)', 'Check', 'Row-level'], summary, { rowHeader: true }));
  // Extra rows used by the rendered selection are already counted via render() above.
  return { id: 'truth-table', label: 'Truth table', node };
}

function countermodelView(P, xc) {
  const sections = P.countermodels.map((c) => {
    const prem = c.premises.map((p) => p.structure); const concl = c.conclusion.structure;
    const jsCm = countermodelJS(prem, concl);
    const jsEnt = entails(prem, concl);
    const verdictMark = xc.mark([c.entails, c.countermodel], [jsEnt, jsCm]);
    const lines = [['Premises', c.premises.map((p) => p.string).join('  ,  ')], ['Conclusion', c.conclusion.string],
      ['Entailed? (Python)', words(c.entails)], ['Entailed? (JS)', words(jsEnt)],
      ['Countermodel (Python)', c.countermodel ? asg(c.countermodel) : 'none'],
      ['Countermodel (JS)', jsCm ? asg(jsCm) : 'none'], ['Check', verdictMark]];
    let extra = null;
    if (jsCm) {
      const pv = prem.map((p) => truthTable(p) && models(p, Object.keys(jsCm)).some((m) => canon(m) === canon(jsCm)));
      const cv = models(concl, Object.keys(jsCm)).some((m) => canon(m) === canon(jsCm));
      extra = h('p', { class: 'text-result' }, `Under that countermodel every premise is ${pv.every(Boolean) ? 'true' : 'NOT all true'} and the conclusion is ${words(cv)}, so the inference is invalid.`);
    } else extra = h('p', { class: 'text-result' }, 'No countermodel exists: the inference is valid.');
    return h('div', { id: `cm-${c.name}` }, h('h3', {}, c.name.replaceAll('_', ' ')), h('p', {}, c.description),
      table(`Result for ${c.name}`, ['Item', 'Value'], lines, { rowHeader: true }), extra);
  });
  return { id: 'countermodel', label: 'Countermodel', node: h('div', {}, sections) };
}

function wumpusView(P, xc) {
  const W = P.wumpus;
  const prem = W.premises.map((p) => p.structure);
  const conj = prem.reduce((a, b) => and(a, b));
  const jsModels = models(conj, W.variables);
  const modelsMark = xc.mark(W.models, jsModels);
  const pitsOf = (m) => Object.keys(m).filter((k) => /^P\d\d$/.test(k) && m[k]);
  const worlds = W.models.map((m, i) => {
    const pits = pitsOf(m);
    const cell = (x, y) => {
      const pit = m[`P${x}${y}`];
      return h('td', { class: pit ? 'pitcell' : 'safecell' }, `(${x},${y})`, h('br'), pit ? 'PIT' : 'no pit');
    };
    const t = table(`World ${i + 1}: pits at ${pits.map((p) => `(${p[1]},${p[2]})`).join(' and ')}`,
      ['', 'x = 1', 'x = 2'], [['y = 2', cell(1, 2), cell(2, 2)], ['y = 1', cell(1, 1), cell(2, 1)]],
      { rowHeader: true, class: 'grid' });
    return h('div', {}, t, h('p', {}, `Outside the 2x2 grid: pit at (3,1) is ${m.P31 ? 'present' : 'absent'}.`));
  });
  // per-cell status recomputed in JS
  const jsStatus = (c) => {
    const pit = entails(prem, vr(c));
    const safe = entails(prem, not(vr(c)));
    return pit ? 'entailed_pit' : safe ? 'entailed_safe' : 'undetermined';
  };
  const label = { entailed_safe: 'entailed safe', entailed_pit: 'entailed pit', undetermined: 'undetermined' };
  const cls = { entailed_safe: 'safe', entailed_pit: 'pit', undetermined: 'undetermined' };
  const statusRows = W.cells.map((c) => {
    const js = jsStatus(c.cell);
    return [c.cell, `(${c.x},${c.y})`, h('span', { class: `badge ${cls[c.status]}`, 'data-cell': c.cell }, label[c.status]),
      h('span', { class: `badge ${cls[js]}` }, label[js]), xc.mark(c.status, js)];
  });
  const statusCell = (name, x, y) => {
    const c = W.cells.find((k) => k.cell === name);
    const k = c.status === 'entailed_safe' ? 'safecell' : c.status === 'entailed_pit' ? 'pitcell' : 'unkcell';
    return h('td', { class: k }, `(${x},${y})`, h('br'), label[c.status]);
  };
  const statusGrid = table('Per-cell status over all 3 worlds (entailed by the KB)', ['', 'x = 1', 'x = 2'],
    [['y = 2', statusCell('P12', 1, 2), statusCell('P22', 2, 2)], ['y = 1', statusCell('P11', 1, 1), statusCell('P21', 2, 1)]],
    { rowHeader: true, class: 'grid' });
  const queryRows = W.queries.map((q) => {
    const f = q.structure; const e = entails(prem, f); const cm = countermodelJS(prem, f);
    return [q.name, mono(q.string), words(q.entails), words(e), q.countermodel ? 'yes' : 'none', xc.mark([q.entails, q.countermodel], [e, cm])];
  });
  const text = W.cells.filter((c) => ['P12', 'P21', 'P22'].includes(c.cell))
    .map((c) => `${c.cell}: ${label[c.status]}`).join('; ');
  const node = h('div', {},
    h('p', { class: 'text-result', id: 'wumpus-text' },
      `The knowledge base has ${W.model_count} possible worlds (Python) and ${jsModels.length} (JS). ${text}.`),
    h('p', {}, 'Mark for the model list: ', modelsMark),
    h('p', { class: 'note' }, W.grid_note),
    h('div', { class: 'worlds', id: 'wumpus-worlds' }, worlds),
    statusGrid,
    table('Cell status, Python vs JS', ['Pit variable', 'Cell', 'Python', 'JS', 'Check'], statusRows, { rowHeader: true }),
    table('Entailment queries on the KB (premises: ' + W.premises.map((p) => p.string).join(' ; ') + ')',
      ['Query', 'Formula', 'Entailed (Py)', 'Entailed (JS)', 'Countermodel', 'Check'], queryRows, { rowHeader: true }));
  return { id: 'wumpus', label: 'Wumpus 2x2 corner', node };
}

function proofView(P, xc) {
  const parts = P.proofs.map((c) => {
    const prem = c.premises.map((p) => p.structure);
    const js = checkProofJS(c.steps.map((s) => ({ formula: s.formula.structure, rule: s.rule, cites: s.cites })), prem);
    const stepRows = c.steps.map((s, i) => [String(i), mono(s.formula.string), s.rule, s.cites.join(', ') || '-',
      c.python.ok ? 'ok' : (i < c.python.bad_step ? 'ok' : i === c.python.bad_step ? 'REJECTED' : 'not checked')]);
    const verdict = (r) => (r.ok ? 'valid proof' : `rejected at step ${r.bad_step}`);
    return h('div', { id: `proof-${c.name}` }, h('h3', {}, c.name.replaceAll('_', ' ')), h('p', {}, c.description),
      table(`Steps of ${c.name} (Python verdict per step)`, ['Step', 'Formula', 'Rule', 'Cites', 'Checker'], stepRows, { rowHeader: true }),
      table('Checker outcome', ['', 'Python', 'JS'], [
        ['Verdict', verdict(c.python), verdict(js)],
        ['Reason', c.python.reason || '(none)', js.reason || '(none)'],
        ['Check (ok and failing step)', xc.mark([c.python.ok, c.python.bad_step], [js.ok, js.bad_step]), ''],
        ['Expected by the test author', c.expect_ok ? 'valid' : 'must be rejected', xc.mark(c.expect_ok, c.python.ok)]], { rowHeader: true }));
  });
  return { id: 'proof-check', label: 'Proof check', node: h('div', {}, parts) };
}

function partialView(P, xc) {
  const rows = P.partial_eval.map((e) => {
    const js = partialJS(e.structure, e.assignment);
    const show = (r) => (r.status === 'known' ? `KNOWN ${words(r.value)}` : `UNKNOWN (${r.reason})`);
    return [e.name, mono(e.string), asg(e.assignment), show(e.python), show(js), xc.mark(e.python, js), e.description];
  });
  return { id: 'partial-eval', label: 'Partial evaluation', node: h('div', {},
    h('p', {}, 'Strong Kleene: a value is KNOWN only when the known parts decide it; otherwise UNKNOWN, with the unassigned variables listed.'),
    table('Strong-Kleene partial evaluation, Python vs JS', ['Case', 'Formula', 'Assignment', 'Python', 'JS', 'Check', 'Why'], rows, { rowHeader: true })) };
}

function inductionView(P, xc) {
  const I = P.induction;
  const jsTri = (n) => { let s = 0; for (let i = 1; i <= n; i++) s += i; return s; };
  const triRows = I.triangular.samples.map((r) => [String(r.n), String(r.iteration), String(r.closed_form), String(jsTri(r.n)),
    xc.mark([r.iteration, r.closed_form], [jsTri(r.n), r.n * (r.n + 1) / 2])]);
  const mir = (t) => (t.leaf ? t : { left: mir(t.right), right: mir(t.left) });
  const eq = (a, b) => canon(a) === canon(b);
  const treeRows = I.mirror.sample_trees.map((s, i) => [String(i + 1), mono(canon(s.tree).replaceAll('"', '')),
    String(s.mirror_of_mirror_equals_original), String(eq(mir(mir(s.tree)), s.tree)),
    xc.mark(s.mirror_of_mirror_equals_original, eq(mir(mir(s.tree)), s.tree))]);
  return { id: 'induction', label: 'Induction checks', node: h('div', {},
    h('p', { class: 'note', id: 'induction-disclaimer' }, I.disclaimer),
    h('p', { class: 'text-result' }, `Triangular numbers: ${I.triangular.checked} values checked (n = ${I.triangular.checked_range[0]} to ${I.triangular.checked_range[1]}), ${I.triangular.failures.length} failures. `
      + `Mirror twice: ${I.mirror.checked} trees checked (${I.mirror.checked_scope}), ${I.mirror.failures.length} failures. `
      + 'No amount of checking proves the claim for all n or all trees. The proofs are in ' + I.triangular.proof_ref.split(' Proof')[0] + '.'),
    table(`Claim: ${I.triangular.claim} (sampled rows; proof: ${I.triangular.proof_ref})`,
      ['n', 'Python iteration', 'closed form', 'JS iteration', 'Check'], triRows, { rowHeader: true }),
    table(`Claim: ${I.mirror.claim} (proof: ${I.mirror.proof_ref}); shapes of 1 to 3 leaves`,
      ['Tree', 'Structure', 'Python: mirror twice = original', 'JS: mirror twice = original', 'Check'], treeRows, { rowHeader: true })) };
}
