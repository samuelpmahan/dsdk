import { createRequire } from 'node:module';
const require = createRequire('/opt/node22/lib/node_modules/');
const { chromium } = require('playwright');
const file = process.argv[2], out = process.argv[3];
const b = await chromium.launch();
const errs = [];
for (const [w,h,tag] of [[1200,900,'desk'],[400,900,'phone']]) {
  const p = await b.newPage({ viewport:{width:w,height:h} });
  p.on('console', m => m.type()==='error' && errs.push(m.text()));
  p.on('pageerror', e => errs.push(String(e)));
  await p.goto('file://' + file);
  await p.click('#cave-run');
  await p.click('#cave-pick'); await p.selectOption('#cave-pick','seed'); 
  const log = await p.$$eval('#cave-log li', ls => ls.map(l=>l.textContent));
  const sw = await p.evaluate(() => document.documentElement.scrollWidth);
  console.log(tag, 'scrollWidth', sw, 'log', log.length);
  await p.selectOption('#cave-pick','demo'); await p.click('#cave-run');
  console.log((await p.$$eval('#cave-log li', ls => ls.map(l=>l.textContent))).join('\n'));
  await p.screenshot({ path: `${out}-${tag}.png`, fullPage: true });
}
// soundness sweep: 300 random caves, agent must never die
const p = await b.newPage();
await p.goto('file://' + file);
const res = await p.evaluate(() => { let died=0, gold=0; const s=document.querySelector('#cave-seed'), pick=document.querySelector('#cave-pick');
  for (let i=1;i<=300;i++){ pick.value='seed'; s.value=String(i); s.dispatchEvent(new Event('change')); let g=80; while(!document.querySelector('#cave-step').disabled && g--) document.querySelector('#cave-step').click();
    const st=document.querySelector('#cave-stats').textContent; if(/died/.test(st)) died++; if(/escaped with gold/.test(st)) gold++; }
  return {died, gold}; });
console.log('sweep', JSON.stringify(res));
// probability rung: both sweeps, dsdk's numbers vs the page's recomputation
await p.click('#sweep2');
const rates = await p.$$eval('#rates-table .rate-check', ts => ts.map(t => t.dataset.agree));
const stuck = await p.$eval('#stuck-check', e => e.textContent);
const rateRows = await p.$$eval('#rates-table tbody tr', rs => rs.map(r => r.textContent));
await p.selectOption('#cave-pick','demo'); await p.check('#cave-prob'); await p.click('#cave-run');
const cells = await p.$$eval('#rung-table .rung-check', ts => ts.map(t => t.dataset.agree));
const demoLog = await p.$$eval('#cave-log li', ls => ls.map(l=>l.textContent));
await p.screenshot({ path: `${out}-rung.png`, fullPage: true });
console.log('rung rates', JSON.stringify(rates), JSON.stringify(rateRows));
console.log('rung stuck', stuck);
console.log('rung demo cells', JSON.stringify(cells));
console.log('rung demo log tail', JSON.stringify(demoLog.slice(-3)));
console.log('errors', JSON.stringify(errs));
await b.close();
