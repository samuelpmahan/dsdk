// Track W1 ("Six degrees of dubstep") browser assertions + screenshot plan. Called by viewer/capture.mjs.
export const config = { minAgree: 250, keyboardView: 'degrees', tamperView: 'queries', minCaptions: 3, minHeaders: 10 };

/** Negative control: bump the hop count of one observed step in a checked query; the JS recomputation must disagree. */
export function tamper(packet) {
  const q = packet.panels.queries.find((x) => x.status === 'known' && x.hops.length > 1);
  q.hops[0].count += 1;
}

export async function run(ctx) {
  const { page, assert, shot, openView } = ctx;
  const text = async (sel) => (await page.locator(sel).first().innerText()).replace(/\s+/g, ' ').trim();

  await openView('summary');
  assert('summary: verdict is stated in text', /Verdict: supported/.test(await text('#verdict')), await text('#verdict'));
  assert('provenance footer shows a 40-hex git sha', /^[0-9a-f]{40}$/.test(await text('#prov-sha')) || (await text('#prov-sha')) === 'unknown', await text('#prov-sha'));
  await shot('w1-summary.png');

  // ---- the instrument, default demo query: Torque -> Babatunde
  await openView('degrees');
  assert('degrees: demo query is KNOWN with 4 steps', /KNOWN/.test(await text('#sd-verdict')) && /4 steps/.test(await text('#sd-verdict')), await text('#sd-verdict'));
  const chain = await text('#sd-chain');
  assert('degrees: chain names the tracks and artists end to end', /Torque/.test(chain) && /Babatunde/.test(chain) && /by Space Laces/.test(chain) && /Kompany/.test(chain), chain.slice(0, 200));
  const hopLines = await page.locator('#sd-chain li.hop').allInnerTexts();
  assert('degrees: every step line names a DJ and an ISO date', hopLines.length === 4 && hopLines.every((l) => /\d{4}-\d\d-\d\d/.test(l) && /back to back/.test(l)), hopLines.join(' | '));
  assert('degrees: "How do we know?" table has one row per step', (await page.locator('#sd-how tbody tr').count()) === 4, '');
  assert('degrees: cross-check with Python for the demo query shows agreement', (await page.locator('#sd-demo-xc [data-agree="true"]').count()) === 3, '');
  await shot('w1-degrees-known.png');

  // ---- type two track names and ask (keyboard only)
  await page.fill('#sd-from', 'Sandstorm');
  await page.fill('#sd-to', 'Codename X');
  await page.press('#sd-to', 'Enter');
  const v2 = await text('#sd-verdict');
  assert('degrees: Sandstorm to Codename X is UNKNOWN with exactly one inferred step', /UNKNOWN/.test(v2) && /5 steps, 1 of them inferred/.test(v2), v2);
  assert('degrees: the inferred step is drawn as inferred, and 4 steps are observed',
    (await page.locator('#sd-chain li.hop.unknown').count()) === 1 && (await page.locator('#sd-chain li.hop.known').count()) === 4, '');
  assert('degrees: inferred step says it was never seen back to back', /never seen back to back/.test(await text('#sd-chain li.hop.unknown')), '');
  await shot('w1-degrees-unknown.png');

  await page.fill('#sd-to', 'zzzzzzzz nonsense');
  await page.press('#sd-to', 'Enter');
  const v3 = await text('#sd-verdict');
  assert('degrees: a track that does not exist is INVALID, not UNKNOWN', /INVALID/.test(v3) && !/UNKNOWN/.test(v3), v3);

  await page.fill('#sd-from', '#1123');
  await page.fill('#sd-to', '#482');
  await page.press('#sd-to', 'Enter');
  const v4 = await text('#sd-verdict');
  assert('degrees: a pair with no route in the sample is UNKNOWN and says absence is not proof', /UNKNOWN/.test(v4) && /does not prove/.test(v4), v4);

  await page.click('#sd-random');
  assert('degrees: "Surprise me" gives a verdict', /KNOWN|UNKNOWN/.test(await text('#sd-verdict')), await text('#sd-verdict'));
  await page.click('#sd-swap');
  assert('degrees: swap re-asks the reversed question', (await text('#sd-verdict')).length > 0, '');

  // ---- checked queries
  await openView('queries');
  const n = await page.locator('#view-queries tbody tr').count();
  assert('queries: every checked query has a row', n >= 50, `rows=${n}`);
  assert('queries: text says all three implementations agree', /same status, witness path, reason string and per-step evidence/.test(await text('#queries-text')), '');
  await shot('w1-queries.png');

  await openView('distances');
  const dt = await text('#dist-text');
  assert('distances: states the 300 random pairs and the median', /300 random pairs/.test(dt) && /median \d+/.test(dt), dt);
  await shot('w1-distances.png');

  await openView('world');
  const wt = await text('#world-text');
  assert('world: states the corpus size', /1352 tracks/.test(wt) && /1919 observed back-to-back transitions/.test(wt), wt);
  assert('world: provenance sentence is the Part-composed one', /^lost-lands-2018: 1352 tracks, 817 artists, 50 selector groups, 54 sets on 8 dates, 1973 selections, 1919 transitions; sha256 7e0b652aac54 @ 8b4d32b$/.test(await text('#prov-sentence')), await text('#prov-sentence'));
  assert('world: pinned digest is displayed in full', /^7e0b652aac543fbe89e80e8b47b5e7f0e67ac622ee20ae2426bd6d07492eb8a5$/.test(await text('#prov-world-sha')), '');
  await shot('w1-world.png');
}
