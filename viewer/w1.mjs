// W1 "Six degrees of dubstep": shortest transition path between two Lost Lands tracks, with evidence.
//
// SELF-CONTAINED instrument. Everything is computed here, in JS, from the jukebox primitive store alone
// (`world` = the decoded JSON of lostlands-2018.jukebox.json.gz, schema jukebox-primitives/v1). Nothing reads Python's
// answers except the evidence `views()` below, which compares the two. The Lab shell can mount just the instrument:
//
//     import { mountSixDegrees, loadWorldFromGzip } from './w1.mjs';
//     const world = await loadWorldFromGzip('fixtures/worlds/lostlands-2018.jukebox.json.gz');
//     mountSixDegrees(document.getElementById('slot'), world, { from: 483, to: 237 });
//
// Vocabulary (never collapsed):
//   KNOWN    every step was seen back-to-back in some DJ's set.
//   UNKNOWN  no all-observed route exists; the best route uses steps that are only INFERRED (the two tracks shared a
//            DJ's set but were never seen back-to-back in that order), or there is no route at all (open world: the
//            corpus is a sample, so "no path found" is not "impossible").
//   INVALID  the question names a track that is not in the corpus.
import { h, table } from './ui.mjs';

export const OPEN_WORLD = 'open world: no path found, but absence of an edge is not proof of impossibility';

// ------------------------------------------------------------------------------------------------ world index
export function buildIndex(world) {
  const n = world.tracks.length;
  const setKey = (g, d) => `${g},${d}`;
  const sets = new Map(); // "g,d" -> [track ids in play order]
  for (const [t, g, d] of world.selections) {
    const k = setKey(g, d);
    if (!sets.has(k)) sets.set(k, []);
    sets.get(k).push(t);
  }
  const seen = new Map(); // "a,b" -> { count, sets: Set<"g,d"> }
  for (const [a, b, g, d] of world.transitions) {
    const k = `${a},${b}`;
    if (!seen.has(k)) seen.set(k, { count: 0, sets: new Set() });
    const e = seen.get(k); e.count += 1; e.sets.add(setKey(g, d));
  }
  const trackSets = Array.from({ length: n }, () => new Set());
  for (const [k, ts] of sets) for (const t of ts) trackSets[t].add(k);
  // successors: Map target -> inferred(bool); observed wins
  const succ = Array.from({ length: n }, () => new Map());
  for (const ts of sets.values()) {
    const u = [...new Set(ts)];
    for (let i = 0; i < u.length; i++) for (let j = 0; j < u.length; j++) if (i !== j) succ[u[i]].set(u[j], true);
  }
  const knownSucc = Array.from({ length: n }, () => []);
  for (const k of seen.keys()) {
    const [a, b] = k.split(',').map(Number);
    succ[a].set(b, false);
    knownSucc[a].push(b);
  }
  for (const l of knownSucc) l.sort((x, y) => x - y);
  const adj = succ.map((m) => [...m.entries()].sort((x, y) => x[0] - y[0]));
  let edges = 0; for (const l of adj) edges += l.length;
  return { world, n, sets, seen, trackSets, adj, knownSucc, edges, knownEdges: seen.size };
}

const setPair = (k) => k.split(',').map((x) => Number(x));
const setOrder = (a, b) => (a[0] - b[0]) || (a[1] - b[1]); // dates are indices in the real corpus (no undated sets)

export function hopOf(idx, a, b) {
  const s = idx.seen.get(`${a},${b}`);
  if (s) return { source: a, target: b, evidence: 'known', count: s.count, sets: [...s.sets].map(setPair).sort(setOrder) };
  if (a !== b && idx.trackSets[a] && idx.trackSets[b]) {
    const both = [...idx.trackSets[a]].filter((k) => idx.trackSets[b].has(k));
    if (both.length) return { source: a, target: b, evidence: 'unknown', count: both.length, sets: both.map(setPair).sort(setOrder) };
  }
  return null;
}

class Heap { // min-heap on cmp
  constructor(cmp) { this.a = []; this.cmp = cmp; }
  get size() { return this.a.length; }
  push(x) {
    const a = this.a; a.push(x); let i = a.length - 1;
    while (i > 0) { const p = (i - 1) >> 1; if (this.cmp(a[i], a[p]) >= 0) break; [a[i], a[p]] = [a[p], a[i]]; i = p; }
  }
  pop() {
    const a = this.a, top = a[0], last = a.pop();
    if (a.length) {
      a[0] = last; let i = 0;
      for (;;) {
        const l = 2 * i + 1, r = l + 1; let m = i;
        if (l < a.length && this.cmp(a[l], a[m]) < 0) m = l;
        if (r < a.length && this.cmp(a[r], a[m]) < 0) m = r;
        if (m === i) break; [a[i], a[m]] = [a[m], a[i]]; i = m;
      }
    }
    return top;
  }
}
const cmpState = (x, y) => {
  if (x[0] !== y[0]) return x[0] - y[0];
  if (x[1] !== y[1]) return x[1] - y[1];
  const p = x[2], q = y[2];
  for (let i = 0; i < Math.min(p.length, q.length); i++) if (p[i] !== q[i]) return p[i] - q[i];
  return p.length - q.length;
};

function knownPath(idx, s, t) {
  const parent = new Map([[s, null]]); const queue = [s];
  for (let qi = 0; qi < queue.length && !parent.has(t); qi++) {
    const u = queue[qi];
    for (const v of idx.knownSucc[u]) if (!parent.has(v)) { parent.set(v, u); queue.push(v); }
  }
  if (!parent.has(t)) return null;
  const out = [t]; while (parent.get(out[out.length - 1]) !== null) out.push(parent.get(out[out.length - 1]));
  return out.reverse();
}
function candidatePath(idx, s, t) {
  const heap = new Heap(cmpState); heap.push([0, 0, [s]]); const settled = new Set();
  while (heap.size) {
    const [unc, hops, path] = heap.pop(); const last = path[path.length - 1];
    if (settled.has(last)) continue;
    settled.add(last);
    if (last === t) return path;
    for (const [v, inferred] of idx.adj[last]) if (!settled.has(v)) heap.push([unc + (inferred ? 1 : 0), hops + 1, [...path, v]]);
  }
  return null;
}

/** Decision table: INVALID -> KNOWN path (BFS over observed steps) -> best path with inferred steps -> open world. */
export function queryDegrees(idx, s, t) {
  const bad = [s, t].find((x) => !Number.isInteger(x) || x < 0 || x >= idx.n);
  if (bad !== undefined) return { status: 'invalid', reason: `node ${bad} is not in the graph`, path: null, hops: [] };
  let path = knownPath(idx, s, t);
  if (path) {
    return { status: 'known', reason: `known path: ${path.join(' -> ')}`, path, hops: path.slice(1).map((v, i) => hopOf(idx, path[i], v)) };
  }
  path = candidatePath(idx, s, t);
  if (!path) return { status: 'unknown', reason: OPEN_WORLD, path: null, hops: [] };
  const hops = path.slice(1).map((v, i) => hopOf(idx, path[i], v));
  const bads = hops.filter((x) => x.evidence !== 'known').map((x) => `${x.source}->${x.target} (${x.evidence})`);
  return { status: 'unknown', reason: `uncertain edges on best candidate path: ${bads.join(', ')}`, path, hops };
}

// ------------------------------------------------------------------------------------------------ labels
export function trackArtists(world, i) { return world.tracks[i][2].map((a) => world.artists[a]).join(' & '); }
export function trackTitle(world, i) { const v = world.tracks[i][4]; return v ? `${world.tracks[i][1]} (${v})` : world.tracks[i][1]; }
export function trackLabel(world, i) { return `${trackArtists(world, i)} - ${trackTitle(world, i)}`; }
const djOf = (world, g) => world.selectorGroups[g][1];
const dateOf = (world, d) => (d === -1 || d === null ? 'undated' : world.dates[d]);

/** Text for a hop's evidence: who played it, when, how often. */
export function hopEvidenceText(world, hop) {
  const shown = hop.sets.slice(0, 3).map(([g, d]) => `${djOf(world, g)} on ${dateOf(world, d)}`);
  const more = hop.sets.length > 3 ? `, and ${hop.sets.length - 3} more set(s)` : '';
  if (hop.evidence === 'known') return `Seen back-to-back ${hop.count}x: ${shown.join('; ')}${more}.`;
  return `Never seen in this order. Both were in ${hop.count} set(s): ${shown.join('; ')}${more}. Inferred, not observed.`;
}

export function resolveTrack(world, text, labels) {
  const q = String(text ?? '').trim();
  if (!q) return { error: 'empty' };
  const m = q.match(/\[#(\d+)\]\s*$/);
  if (m) { const id = Number(m[1]); return id < world.tracks.length ? { id } : { error: `no track #${id}` }; }
  if (/^#?\d+$/.test(q)) { const id = Number(q.replace('#', '')); return id < world.tracks.length ? { id } : { error: `no track #${id}` }; }
  const low = q.toLowerCase();
  let hit = labels.findIndex((l) => l.toLowerCase() === low);
  if (hit < 0) hit = labels.findIndex((l) => l.toLowerCase().includes(low));
  return hit >= 0 ? { id: hit } : { error: `no track matches "${q}"` };
}

// ------------------------------------------------------------------------------------------------ the instrument UI
const STYLE = `
.sd { font: inherit; color: inherit; }
.sd form { display: grid; grid-template-columns: 1fr 1fr; gap: 8px 16px; align-items: end; margin: 8px 0; }
.sd label { display: block; font-weight: 600; margin: 0 0 2px; }
.sd input[type=text] { width: 100%; font: inherit; padding: 8px; border: 1px solid var(--line, #d0d7de); border-radius: 6px; background: var(--bg, #fff); color: inherit; }
.sd .row { grid-column: 1 / -1; display: flex; flex-wrap: wrap; gap: 8px; }
.sd button { font: inherit; padding: 8px 14px; border: 1px solid var(--line, #d0d7de); border-radius: 6px; background: var(--panel, #f6f8fa); color: inherit; cursor: pointer; }
.sd button.go { background: var(--accent, #0b5cad); color: var(--bg, #fff); border-color: var(--accent, #0b5cad); font-weight: 600; }
.sd .verdict { margin: 12px 0 4px; font-weight: 600; }
.sd ol.chain { list-style: none; margin: 8px 0; padding: 0; }
.sd ol.chain li.track { border: 1px solid var(--line, #d0d7de); border-radius: 8px; padding: 8px 12px; background: var(--panel, #f6f8fa); }
.sd ol.chain li.track .title { font-weight: 700; }
.sd ol.chain li.track .artist { color: var(--muted, #57606a); }
.sd ol.chain li.hop { margin: 0 0 0 20px; padding: 6px 12px; border-left: 4px solid var(--line, #d0d7de); font-size: .92rem; }
.sd ol.chain li.hop.known { border-left-color: var(--ok-fg, #0a5c1f); }
.sd ol.chain li.hop.unknown { border-left-color: var(--unk-fg, #6b4a00); border-left-style: dashed; }
.sd .tag { display: inline-block; padding: 0 8px; border-radius: 4px; font-weight: 600; font-size: .85rem; }
.sd .tag.known { background: var(--ok-bg, #dafbe1); color: var(--ok-fg, #0a5c1f); }
.sd .tag.unknown { background: var(--unk-bg, #fff3c4); color: var(--unk-fg, #6b4a00); }
.sd .tag.invalid { background: var(--bad-bg, #ffd8d3); color: var(--bad-fg, #8b1a10); }
.sd details { margin: 12px 0; border: 1px solid var(--line, #d0d7de); border-radius: 8px; padding: 6px 12px; }
.sd summary { cursor: pointer; font-weight: 600; }
@media (max-width: 600px) { .sd form { grid-template-columns: 1fr; } }
`;

export function mountSixDegrees(root, world, opts = {}) {
  if (!document.getElementById('sd-style')) document.head.append(h('style', { id: 'sd-style' }, STYLE));
  const idx = opts.index || buildIndex(world);
  const labels = world.tracks.map((_, i) => trackLabel(world, i));
  const uid = opts.id || 'sd';
  const listId = `${uid}-tracks`;
  const dl = h('datalist', { id: listId }, labels.map((l, i) => h('option', { value: `${l} [#${i}]` })));
  const fromIn = h('input', { type: 'text', id: `${uid}-from`, list: listId, autocomplete: 'off', placeholder: 'e.g. Torque' });
  const toIn = h('input', { type: 'text', id: `${uid}-to`, list: listId, autocomplete: 'off', placeholder: 'e.g. Babatunde' });
  const verdict = h('p', { class: 'verdict', id: `${uid}-verdict`, role: 'status', 'aria-live': 'polite' });
  const chain = h('ol', { class: 'chain', id: `${uid}-chain`, 'aria-label': 'Transition path' });
  const how = h('details', { id: `${uid}-how`, open: true });
  const go = h('button', { type: 'submit', class: 'go', id: `${uid}-go` }, 'Find the path');
  const swap = h('button', { type: 'button', id: `${uid}-swap` }, 'Swap');
  const rnd = h('button', { type: 'button', id: `${uid}-random` }, 'Surprise me');
  const form = h('form', { id: `${uid}-form` },
    h('div', {}, h('label', { for: `${uid}-from` }, 'From track'), fromIn),
    h('div', {}, h('label', { for: `${uid}-to` }, 'To track'), toIn),
    h('div', { class: 'row' }, go, swap, rnd));
  const state = { last: null, seed: 2018 };
  const nextRandom = () => { state.seed = (state.seed * 1103515245 + 12345) % 2147483648; return state.seed; };
  const tag = (status) => h('span', { class: `tag ${status}` }, status.toUpperCase());

  function render(res, s, t) {
    state.last = { res, s, t };
    chain.replaceChildren(); how.replaceChildren();
    root.dataset.status = res.status; root.dataset.hops = res.path ? String(res.path.length - 1) : ''; root.dataset.path = res.path ? res.path.join(',') : '';
    if (res.status === 'invalid') {
      verdict.replaceChildren(tag('invalid'), ` ${res.reason}. That track is not in the corpus, so no question about it can be answered (this is different from "unknown").`);
      return;
    }
    if (!res.path) {
      verdict.replaceChildren(tag('unknown'), ' No route found between these tracks in the sampled corpus. That does not prove there is none: this corpus is a sample (open world).');
      how.append(h('summary', {}, 'How do we know?'), h('p', {}, `Reason: ${res.reason}.`));
      return;
    }
    const inferred = res.hops.filter((x) => x.evidence !== 'known').length;
    const steps = res.hops.length;
    verdict.replaceChildren(tag(res.status),
      res.status === 'known'
        ? ` ${steps} step${steps === 1 ? '' : 's'}, every one seen back-to-back in a real set.`
        : ` ${steps} step${steps === 1 ? '' : 's'}, ${inferred} of them inferred (never seen in that order, only co-selected). The fewest inferred steps wins.`);
    res.path.forEach((id, i) => {
      chain.append(h('li', { class: 'track', 'data-track': String(id) },
        h('span', { class: 'title' }, trackTitle(world, id)), ' ', h('span', { class: 'artist' }, `by ${trackArtists(world, id)}`)));
      const hp = res.hops[i];
      if (hp) {
        const [g0, d0] = hp.sets[0];
        const more = hp.sets.length > 1 ? ` (and ${hp.sets.length - 1} other set${hp.sets.length > 2 ? 's' : ''})` : '';
        chain.append(h('li', { class: `hop ${hp.evidence}`, 'data-evidence': hp.evidence },
          hp.evidence === 'known'
            ? `${djOf(world, g0)} played these two back to back on ${dateOf(world, d0)}${more}`
            : `inferred, never seen back to back: both were in ${djOf(world, g0)}'s set on ${dateOf(world, d0)}${more}`));
      }
    });
    const rows = res.hops.map((hp, i) => [`${i + 1}. ${labels[hp.source]}  →  ${labels[hp.target]}`, hp.evidence.toUpperCase(), hopEvidenceText(world, hp)]);
    how.append(h('summary', {}, 'How do we know?'),
      h('p', {}, res.status === 'known'
        ? 'KNOWN means each step is an observed transition: a DJ played these two tracks one right after the other.'
        : 'UNKNOWN means at least one step is inferred: the two tracks shared a DJ\'s set but were never seen back-to-back in this order.'),
      rows.length ? table('Evidence for each step', ['Step', 'Status', 'Evidence'], rows) : h('p', {}, 'Same track: the empty path.'),
      h('p', { class: 'mono' }, res.reason));
  }

  function ask(s, t) { const res = queryDegrees(idx, s, t); render(res, s, t); return res; }
  function submit() {
    const a = resolveTrack(world, fromIn.value, labels), b = resolveTrack(world, toIn.value, labels);
    if (a.error || b.error) {
      const bad = a.error ? a.error : b.error;
      render({ status: 'invalid', reason: bad, path: null, hops: [] }, null, null);
      verdict.replaceChildren(tag('invalid'), ` ${bad}. Pick a track from the suggestions.`);
      return null;
    }
    return ask(a.id, b.id);
  }
  function set(s, t) { fromIn.value = `${labels[s]} [#${s}]`; toIn.value = `${labels[t]} [#${t}]`; return ask(s, t); }
  form.addEventListener('submit', (e) => { e.preventDefault(); submit(); });
  swap.addEventListener('click', () => { [fromIn.value, toIn.value] = [toIn.value, fromIn.value]; submit(); });
  rnd.addEventListener('click', () => set(nextRandom() % idx.n, nextRandom() % idx.n));

  root.classList.add('sd');
  root.replaceChildren(
    h('p', {}, 'How many back-to-back moves separate two dubstep tracks? Search any two of the ', String(idx.n),
      ' tracks played at Lost Lands 2018.'), form, dl, verdict, chain, how);
  if (opts.from !== undefined && opts.to !== undefined) set(opts.from, opts.to);
  return { ask, set, submit, idx, labels, state };
}

export async function loadWorldFromGzip(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`HTTP ${res.status} for ${url}`);
  const bytes = await res.arrayBuffer();
  const stream = new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'));
  return JSON.parse(await new Response(stream).text());
}

// ------------------------------------------------------------------------------------------------ evidence views
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const hopKey = (x) => ({ source: x.source, target: x.target, evidence: x.evidence, count: x.count, sets: x.sets });

function median(xs) { const s = [...xs].sort((a, b) => a - b); const m = s.length >> 1; return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2; }

export function views(packet, { xc }) {
  const world = packet.panels.world;
  const idx = buildIndex(world);
  const P = packet.panels;

  // ---- interactive instrument
  const slot = h('div', { id: 'sd-slot' });
  const inst = mountSixDegrees(slot, world, { index: idx, from: P.demo.source, to: P.demo.target });
  const demoPy = P.queries.find((q) => q.source === P.demo.source && q.target === P.demo.target);
  const demoJs = queryDegrees(idx, P.demo.source, P.demo.target);
  const demoNote = h('p', { class: 'note', id: 'sd-demo-xc' }, 'Demo query recomputed in JS from the embedded corpus, compared with Python (dsdk.worlds): ',
    xc.mark(demoPy.status, demoJs.status), ' ', xc.mark(demoPy.path, demoJs.path), ' ', xc.mark(demoPy.hops.map(hopKey), demoJs.hops.map(hopKey)));
  const degrees = h('div', {}, demoNote, slot);

  // ---- precomputed queries: Python (dsdk.worlds) vs independent oracle script vs JS
  const qrows = P.queries.map((q, i) => {
    const js = queryDegrees(idx, q.source, q.target);
    return [String(i), `${q.source} → ${q.target}`, q.status, js.status, xc.mark(q.status, js.status),
      q.path ? String(q.path.length - 1) : '-', xc.mark(q.path, js.path), xc.mark(q.reason, js.reason),
      xc.mark(q.hops.map(hopKey), js.hops.map(hopKey)), xc.mark(q.oracle_agrees, true)];
  });
  const queries = h('div', {}, h('p', { id: 'queries-text' }, `${P.queries.length} queries: dsdk.worlds (Python), the independent oracle script `,
    h('code', {}, 'fixtures/worlds/gen_slices.py'), ' (for the fixture cases) and this page\'s JS all give the same status, witness path, reason string and per-step evidence.'),
    table('Python vs JS per query', ['#', 'Query (track ids)', 'Python status', 'JS status', 'status', 'hops', 'path', 'reason', 'step evidence', 'oracle agrees'], qrows));

  // ---- how far apart? (seeded random pairs)
  const ds = P.distances;
  const jsRes = ds.pairs.map(([s, t]) => queryDegrees(idx, s, t));
  const count = (st) => jsRes.filter((r) => r.status === st && (st !== 'unknown' || r.path)).length;
  const jsKnownHops = jsRes.filter((r) => r.status === 'known').map((r) => r.path.length - 1);
  const jsNeeds = jsRes.filter((r) => r.status === 'unknown' && r.path).length;
  const jsOpen = jsRes.filter((r) => r.status === 'unknown' && !r.path).length;
  const hist = {}; for (const k of jsKnownHops) hist[k] = (hist[k] || 0) + 1;
  const jsSummary = { pairs: ds.pairs.length, known: count('known'), needs_inferred: jsNeeds, open_world: jsOpen,
    median_known_hops: jsKnownHops.length ? median(jsKnownHops) : null, max_known_hops: jsKnownHops.length ? Math.max(...jsKnownHops) : null };
  const dist = h('div', {},
    h('p', { id: 'dist-text', class: 'text-result' }, `${ds.summary.pairs} random pairs of tracks (seed ${ds.seed}): ${jsSummary.known} connected by observed steps only (median ${jsSummary.median_known_hops} hops, longest ${jsSummary.max_known_hops}), ${jsSummary.needs_inferred} need at least one inferred step, ${jsSummary.open_world} have no route in this sample.`),
    table('Python vs JS summary of the random pairs', ['Measure', 'Python', 'JS', 'Check'],
      Object.keys(jsSummary).map((k) => [k, String(ds.summary[k]), String(jsSummary[k]), xc.mark(ds.summary[k], jsSummary[k])]), { rowHeader: true }),
    table('How many observed hops apart? (pairs connected by observed steps only)', ['Hops', 'Pairs (Python)', 'Pairs (JS)', 'Check'],
      Object.keys({ ...ds.histogram, ...hist }).map(Number).sort((a, b) => a - b).map((k) => [String(k), String(ds.histogram[k] || 0), String(hist[k] || 0), xc.mark(ds.histogram[k] || 0, hist[k] || 0)])),
    h('p', {}, 'Every pair, per pair: ', xc.mark(ds.results, jsRes.map((r) => [r.status, r.path ? r.path.length - 1 : null])), ' (status and hop count of all pairs, Python vs JS).'));

  // ---- the corpus and its provenance
  const g = P.graph_totals;
  const jsTotals = { tracks: world.tracks.length, artists: world.artists.length, selector_groups: world.selectorGroups.length, dates: world.dates.length,
    selections: world.selections.length, transitions: world.transitions.length, sets: idx.sets.size,
    observed_edges: idx.knownEdges, search_edges: idx.edges };
  const prov = P.provenance;
  const jsSentence = `${world.meta.corpus}: ${jsTotals.tracks} tracks, ${jsTotals.artists} artists, ${jsTotals.selector_groups} selector groups, ${jsTotals.sets} sets on ${jsTotals.dates} dates, ${jsTotals.selections} selections, ${jsTotals.transitions} transitions; sha256 ${prov.sha256.slice(0, 12)} @ ${prov.commit.slice(0, 7)}`;
  const worldView = h('div', {},
    h('p', { id: 'world-text' }, `The corpus is derived data from jukebox (${prov.repo}, branch ${prov.branch}, commit ${prov.commit.slice(0, 7)}): ${jsTotals.tracks} tracks, ${jsTotals.selector_groups} DJ credits, ${jsTotals.sets} sets, ${jsTotals.transitions} observed back-to-back transitions. It contains no raw tracklist lines.`),
    table('Counts: Python vs JS recount of the embedded corpus', ['Measure', 'Python', 'JS', 'Check'],
      Object.keys(jsTotals).map((k) => [k, String(g[k]), String(jsTotals[k]), xc.mark(g[k], jsTotals[k])]), { rowHeader: true }),
    h('h3', {}, 'Provenance as dsdk.core Parts'),
    h('p', { class: 'mono', id: 'prov-sentence' }, prov.sentence), h('p', {}, 'Recomputed sentence matches: ', xc.mark(prov.sentence, jsSentence)),
    table('Source pins', ['Item', 'Value'], [['SHA-256 of the gzip (pinned in jukebox\'s Pages workflow)', h('span', { class: 'mono', id: 'prov-world-sha' }, prov.sha256)],
      ['Branch commit', h('span', { class: 'mono' }, prov.commit)], ['Integrity check', prov.integrity_note]], { rowHeader: true }),
    h('h3', {}, 'What the words mean'),
    table('Evidence vocabulary', ['Word', 'Meaning here'], [
      ['KNOWN', 'A DJ was seen playing track B right after track A (an observed transition).'],
      ['UNKNOWN (inferred)', 'Two tracks were in the same DJ\'s set but never seen back-to-back in this order. Plausible, not observed. Also used when no route exists: the corpus is a sample, so absence proves nothing.'],
      ['NOT OBSERVED', 'Nobody looked: no edge is drawn at all.'],
      ['INVALID', 'The question names a track that is not in the corpus.']], { rowHeader: true }));

  return [
    { id: 'degrees', label: 'Six degrees', node: degrees },
    { id: 'queries', label: 'Checked queries', node: queries },
    { id: 'distances', label: 'How far apart?', node: dist },
    { id: 'world', label: 'The corpus', node: worldView },
  ];
}
