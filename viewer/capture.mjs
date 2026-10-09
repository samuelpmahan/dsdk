// Usage: node viewer/capture.mjs A1
// Serves the repo statically, opens the viewer in headless Chromium, asserts from the DOM, takes full-page PNGs,
// writes tracks/<T>/evidence/capture.json, exits non-zero if any assertion fails.
import http from 'node:http';
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { execSync } from 'node:child_process';
import { createRequire } from 'node:module';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const track = (process.argv[2] || '').toUpperCase();
if (!/^[A-Z][0-9]+$/.test(track)) { console.error('usage: node viewer/capture.mjs <TRACK, e.g. A1>'); process.exit(2); }
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const evDir = path.join(root, 'tracks', track, 'evidence');
const packetRel = `tracks/${track}/evidence/packet.json`;
const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || '/opt/node22/lib/node_modules/playwright');
const trackChecks = await import(pathToFileURL(path.join(root, 'viewer', 'checks', `${track.toLowerCase()}.mjs`)).href);

const MIME = { '.html': 'text/html; charset=utf-8', '.mjs': 'text/javascript; charset=utf-8', '.js': 'text/javascript; charset=utf-8',
  '.json': 'application/json', '.png': 'image/png', '.css': 'text/css', '.md': 'text/plain; charset=utf-8' };
const TAMPER = '/__tampered/packet.json';

// Tiny static server. In-memory tampered packet: the first truth-table row value of the first case is flipped, so a
// viewer that really recomputes must show a disagree mark (negative control for "zero disagree").
// Generic hook: a track's checks module may export `tamper(packet)` (mutate the parsed packet in place) and a `config`
// object { minAgree, keyboardView, tamperView }. Without `tamper`, the first row of the first panel entry that has rows is
// flipped (booleans negated, numbers incremented, strings suffixed), which covers A1 (panels.truth_tables) unchanged.
const cfg = { minAgree: 50, minCaptions: 5, minHeaders: 20, keyboardView: 'wumpus', tamperView: 'truth-table', ...(trackChecks.config || {}) };
function defaultTamper(p) {
  for (const val of Object.values(p.panels || {})) {
    const row = Array.isArray(val) && val[0] && Array.isArray(val[0].rows) ? val[0].rows[0] : null;
    if (!row) continue;
    const key = 'value' in row ? 'value' : Object.keys(row)[0];
    const v = row[key];
    row[key] = typeof v === 'boolean' ? !v : typeof v === 'number' ? v + 1 : `${v}!`;
    return;
  }
  throw new Error('no tamperable row found: export tamper(packet) from the track checks');
}
async function tamperedPacket() {
  const p = JSON.parse(await readFile(path.join(root, packetRel), 'utf8'));
  (trackChecks.tamper || defaultTamper)(p);
  return JSON.stringify(p);
}
const server = http.createServer(async (req, res) => {
  try {
    const url = new URL(req.url, 'http://x');
    if (url.pathname === TAMPER) { res.writeHead(200, { 'content-type': MIME['.json'] }); return res.end(await tamperedPacket()); }
    const file = path.normalize(path.join(root, decodeURIComponent(url.pathname)));
    if (file !== root && !file.startsWith(root + path.sep)) { res.writeHead(403); return res.end('forbidden'); }
    const body = await readFile(file);
    res.writeHead(200, { 'content-type': MIME[path.extname(file)] || 'application/octet-stream', 'cache-control': 'no-store' });
    res.end(body);
  } catch { res.writeHead(404); res.end('not found'); }
});
await new Promise((r) => server.listen(0, '127.0.0.1', r));
const base = `http://127.0.0.1:${server.address().port}`;

const results = []; const shots = []; const consoleProblems = [];
const assert = (name, ok, detail = '') => {
  results.push({ name, passed: Boolean(ok), detail: String(detail).slice(0, 300) });
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${ok ? '' : `  [${String(detail).slice(0, 200)}]`}`);
};

await mkdir(evDir, { recursive: true });
const browser = await chromium.launch({ headless: true });
const viewport = { width: 1280, height: 900 };
let browserVersion = browser.version();
try {
  const context = await browser.newContext({ viewport, deviceScaleFactor: 1, colorScheme: 'light' });
  const page = await context.newPage();
  page.on('pageerror', (e) => consoleProblems.push(`pageerror: ${e.message}`));
  page.on('console', (m) => { if (m.type() === 'error') consoleProblems.push(`console.error: ${m.text()}`); });
  page.on('requestfailed', (r) => consoleProblems.push(`requestfailed: ${r.url()}`));

  const open = async (packet) => {
    await page.goto(`${base}/viewer/index.html?packet=${packet}`);
    await page.waitForFunction(() => document.documentElement.dataset.load, null, { timeout: 15000 });
  };

  await open(`../${packetRel}`);
  assert('viewer loaded the packet without a load error', (await page.getAttribute('html', 'data-load')) === 'ready', await page.locator('#error').innerText());

  // ---- keyboard navigation: Tab from the top of the page must reach skip link, every view button, and the download link
  const ids = await page.$$eval('#views button', (b) => b.map((x) => x.id));
  await page.evaluate(() => { document.activeElement?.blur(); window.scrollTo(0, 0); });
  const visited = [];
  for (let i = 0; i < ids.length + 6; i++) {
    await page.keyboard.press('Tab');
    visited.push(await page.evaluate(() => document.activeElement.id || document.activeElement.className || document.activeElement.tagName));
  }
  const reachedAll = ids.every((id) => visited.includes(id));
  assert('keyboard: Tab reaches the skip link, all view buttons and the download link',
    reachedAll && visited.includes('download') && (await page.locator('a.skip').count()) === 1, visited.join(' > '));
  await page.focus(`#btn-${cfg.keyboardView}`);
  await page.keyboard.press('Enter');
  assert('keyboard: Enter on a focused view button opens that view',
    await page.locator(`#view-${cfg.keyboardView}`).isVisible() && !(await page.locator('#view-summary').isVisible()), '');
  await page.focus('#btn-summary');
  await page.keyboard.press('Space');
  assert('keyboard: Space on a focused view button opens that view', await page.locator('#view-summary').isVisible(), '');

  const openView = async (id) => {
    await page.focus(`#btn-${id}`);
    await page.keyboard.press('Enter');
    await page.waitForSelector(`#view-${id}:not([hidden])`);
  };
  const shot = async (name) => {
    await page.screenshot({ path: path.join(evDir, name), fullPage: true });
    shots.push(name); console.log(`shot  ${path.relative(root, path.join(evDir, name))}`);
  };

  // ---- generic cross-check assertions (all views are in the DOM, hidden ones included)
  const agree = await page.locator('[data-agree="true"]').count();
  const disagree = await page.locator('[data-agree="false"]').count();
  assert('cross-check: zero disagree marks', disagree === 0, `disagree=${disagree}`);
  assert('cross-check: marks are actually present (not vacuous)', agree >= cfg.minAgree, `agree=${agree}`);
  assert('download link is a data: URL of the packet', ((await page.getAttribute('#download', 'href')) || '').startsWith('data:application/json'), '');
  assert('page has tables with captions and header cells',
    (await page.locator("table caption").count()) > cfg.minCaptions && (await page.locator('table th[scope="col"]').count()) > cfg.minHeaders, '');

  // ---- track-specific assertions + screenshots
  await trackChecks.run({ page, assert, shot, openView });
  const finalDisagree = await page.locator('[data-agree="false"]').count();
  assert('cross-check: still zero disagree marks after all interactions', finalDisagree === 0, `disagree=${finalDisagree}`);
  assert('no console errors, page errors or failed requests', consoleProblems.length === 0, consoleProblems.join(' | '));

  // ---- negative control: a tampered packet MUST produce a disagree mark (proves the check can fail)
  await open(TAMPER);
  const tampered = await page.locator('[data-agree="false"]').count();
  assert('negative control: tampered packet is flagged with disagree marks', tampered > 0, `disagree=${tampered}`);
  await openView(cfg.tamperView);
  await shot(`${track.toLowerCase()}-tamper-control.png`);
  await context.close();
} catch (e) {
  assert('capture ran to completion', false, e.stack || e.message);
} finally {
  await browser.close();
  server.close();
}

const failed = results.filter((r) => !r.passed);
let sha = 'unknown'; try { sha = execSync('git rev-parse HEAD', { cwd: root }).toString().trim(); } catch {}
const record = { track, captured_at: new Date().toISOString(), git_sha: sha, browser: { name: 'chromium', version: browserVersion },
  viewport, packet: packetRel, assertions_total: results.length, assertions_passed: results.length - failed.length,
  assertions_failed: failed.length, ok: failed.length === 0, assertions: results, screenshots: shots };
await writeFile(path.join(evDir, 'capture.json'), JSON.stringify(record, null, 1) + '\n');
console.log(`\n${record.assertions_passed}/${record.assertions_total} assertions passed; ${shots.length} screenshots; wrote ${path.relative(root, path.join(evDir, 'capture.json'))}`);
process.exit(failed.length ? 1 : 0);
