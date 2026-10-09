// Parity tests: the JS logic must reproduce the Python-verified fixtures exactly.
// Run: node --test viewer/parity/*.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { toStr, variables, size, evaluate, models, truthTable, entails } from './logic.mjs';

const root = new URL('../../fixtures/logic/', import.meta.url);
const formulas = JSON.parse(readFileSync(new URL('formulas.json', root)));
const kb = JSON.parse(readFileSync(new URL('wumpus_kb.json', root)));

for (const c of formulas.cases) {
  test(`${c.name}: canonical string matches the Python fixture`, () => {
    assert.equal(toStr(c.structure), c.string);
  });
  test(`${c.name}: variables and size match`, () => {
    assert.deepEqual(variables(c.structure), c.variables);
    assert.equal(size(c.structure), c.size);
  });
  test(`${c.name}: truth table matches row for row (same enumeration order)`, () => {
    assert.deepEqual(truthTable(c.structure), c.truth_table);
  });
  test(`${c.name}: model count, satisfiable and valid agree`, () => {
    const ms = models(c.structure);
    assert.equal(ms.length, c.model_count);
    assert.equal(ms.length > 0, c.satisfiable);
    assert.equal(truthTable(c.structure).every((r) => r.value), c.valid);
  });
}

test('evaluate throws naming the unassigned variable (no silent false)', () => {
  const f = { op: 'and', left: { op: 'var', name: 'x' }, right: { op: 'var', name: 'y' } };
  assert.throws(() => evaluate(f, { x: true }), /y/);
});

test('evaluate checks every variable even when short-circuit would skip it', () => {
  const f = { op: 'and', left: { op: 'const', value: false }, right: { op: 'var', name: 'y' } };
  assert.throws(() => evaluate(f, {}), /y/);
});

test('Wumpus KB: exactly the fixture models, in fixture order', () => {
  const conj = kb.premises.map((p) => p.structure)
    .reduce((a, b) => ({ op: 'and', left: a, right: b }));
  assert.deepEqual(models(conj, kb.variables), kb.models);
});

test('Wumpus KB: entailment verdicts match (no pit at 1,2 or 2,1; P22 undetermined)', () => {
  const premises = kb.premises.map((p) => p.structure);
  const v = (name) => ({ op: 'var', name });
  const not = (operand) => ({ op: 'not', operand });
  assert.equal(entails(premises, not(v('P12'))), true, 'no breeze at (1,1) rules out a pit at (1,2)');
  assert.equal(entails(premises, not(v('P21'))), true, 'no breeze at (1,1) rules out a pit at (2,1)');
  assert.equal(entails(premises, v('P22')), false, 'P22 is possible but not forced');
  assert.equal(entails(premises, not(v('P22'))), false, 'P22 is not ruled out either');
  assert.equal(entails(premises, { op: 'or', left: v('P22'), right: v('P31') }), true,
    'the breeze at (2,1) forces a pit at (2,2) or (3,1)');
});

test('entails with no premises is validity', () => {
  const x = { op: 'var', name: 'x' };
  assert.equal(entails([], { op: 'or', left: x, right: { op: 'not', operand: x } }), true);
  assert.equal(entails([], x), false);
});
