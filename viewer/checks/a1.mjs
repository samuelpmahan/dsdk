// Track A1 browser assertions + screenshot plan. Called by viewer/capture.mjs.
// ctx: { page, assert(name, ok, detail), shot(fileName), openView(id) }  (openView uses the keyboard)

export async function run(ctx) {
  const { page, assert, shot, openView } = ctx;
  const text = async (sel) => (await page.locator(sel).first().innerText()).replace(/\s+/g, ' ').trim();

  await openView('summary');
  assert('summary: verdict is stated in text', /Verdict: supported/.test(await text('#verdict')), await text('#verdict'));
  assert('provenance footer shows a 40-hex git sha', /^[0-9a-f]{40}$/.test(await text('#prov-sha')), await text('#prov-sha'));
  assert('provenance footer shows the generated time', /^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$/.test(await text('#prov-time')), await text('#prov-time'));
  await shot('a1-summary.png');

  await openView('truth-table');
  const tt = await text('#tt-text');
  assert('truth table: textual result present', /row\(s\) and \d+ model\(s\) in Python and \d+ in JS/.test(tt), tt);
  const ttRows = await page.locator('#tt-detail tbody tr').count();
  assert('truth table: default (3-variable) table has 8 rows', ttRows === 8, `rows=${ttRows}`);
  // Keyboard-only change of the selected formula: focus the select and use the arrow key.
  const before = await text('#tt-text');
  await page.focus('#tt-select');
  await page.keyboard.press('ArrowDown');
  const after = await text('#tt-text');
  assert('truth table: formula selector changes the table from the keyboard', before !== after, `${before} -> ${after}`);
  await page.selectOption('#tt-select', 'distribution');
  await shot('a1-truth-table.png');

  await openView('countermodel');
  const ac = await text('#cm-affirming_consequent');
  assert('countermodel: affirming the consequent has countermodel p=F q=T in Python and JS',
    (ac.match(/p=F q=T/g) || []).length === 2 && /inference is invalid/.test(ac), ac.slice(0, 300));
  assert('countermodel: a valid inference states that no countermodel exists', /No countermodel exists/.test(await text('#cm-modus_ponens_valid')), '');
  await shot('a1-countermodel.png');

  await openView('wumpus');
  const wt = await text('#wumpus-text');
  assert('wumpus: 3 possible worlds in Python and JS', /3 possible worlds \(Python\) and 3 \(JS\)/.test(wt), wt);
  assert('wumpus: exactly 3 world grids drawn', (await page.locator('#wumpus-worlds table').count()) === 3, '');
  const badge = async (c) => (await page.locator(`[data-cell="${c}"]`).first().innerText()).trim();
  assert('wumpus: P12 is entailed safe', (await badge('P12')) === 'entailed safe', await badge('P12'));
  assert('wumpus: P21 is entailed safe', (await badge('P21')) === 'entailed safe', await badge('P21'));
  assert('wumpus: P22 is undetermined', (await badge('P22')) === 'undetermined', await badge('P22'));
  await shot('a1-wumpus.png');

  await openView('proof-check');
  const bad = await text('#proof-invalid_affirming_consequent');
  assert('proof check: affirming the consequent is rejected at step 2 by both checkers',
    (bad.match(/rejected at step 2/g) || []).length === 2 && /requires Implies\(p, q\) and p, concluding q/.test(bad), bad.slice(0, 400));
  assert('proof check: valid proof accepted', /valid proof/.test(await text('#proof-valid_modus_ponens')), '');
  await shot('a1-proof-check.png');

  await openView('partial-eval');
  const pe = await text('#view-partial-eval');
  assert('partial eval: KNOWN false for false AND x and UNKNOWN for x OR ~x',
    /false_and_unknown[^|]*KNOWN false/.test(pe) && /excluded_middle_unknown[^|]*UNKNOWN \(unassigned: x\)/.test(pe), pe.slice(0, 300));
  await shot('a1-partial-eval.png');

  await openView('induction');
  const note = await text('#induction-disclaimer');
  assert('induction: states that checks do not prove the claims and PROOFS.md does',
    /do not prove/.test(note) && /PROOFS\.md/.test(note), note);
  await shot('a1-induction.png');
}
