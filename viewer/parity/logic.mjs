// Independent JS counterpart of dsdk.logic (A1), used for B3 Python/JS parity.
// It shares no code with the Python side; the shared JSON fixtures are the only contract.
// Formula encoding = the fixtures' "structure" objects:
//   {op:"const",value}, {op:"var",name}, {op:"not",operand},
//   {op:"and"|"or"|"implies"|"iff", left, right}

const BINARY_SYMBOLS = {
  and: '&',
  or: '|',
  implies: '->',
  iff: '<->',
};

function checkOp(f) {
  if (f === null || typeof f !== 'object') {
    throw new Error(`invalid formula node: ${String(f)}`);
  }
}

function collectNames(f, out) {
  checkOp(f);
  switch (f.op) {
    case 'const':
      return out;
    case 'var':
      out.add(f.name);
      return out;
    case 'not':
      return collectNames(f.operand, out);
    case 'and':
    case 'or':
    case 'implies':
    case 'iff':
      collectNames(f.left, out);
      return collectNames(f.right, out);
    default:
      throw new Error(`unknown op: ${String(f.op)}`);
  }
}

/** Canonical fully-parenthesised string; must equal the fixture "string" field. */
export function toStr(f) {
  checkOp(f);
  switch (f.op) {
    case 'const':
      return f.value ? 'true' : 'false';
    case 'var':
      return f.name;
    case 'not':
      return `(~${toStr(f.operand)})`;
    case 'and':
    case 'or':
    case 'implies':
    case 'iff':
      return `(${toStr(f.left)} ${BINARY_SYMBOLS[f.op]} ${toStr(f.right)})`;
    default:
      throw new Error(`unknown op: ${String(f.op)}`);
  }
}

/** Sorted array of distinct variable names. */
export function variables(f) {
  return [...collectNames(f, new Set())].sort();
}

/** Node count (every const/var/not/binary node counts 1). */
export function size(f) {
  checkOp(f);
  switch (f.op) {
    case 'const':
    case 'var':
      return 1;
    case 'not':
      return 1 + size(f.operand);
    case 'and':
    case 'or':
    case 'implies':
    case 'iff':
      return 1 + size(f.left) + size(f.right);
    default:
      throw new Error(`unknown op: ${String(f.op)}`);
  }
}

// Recursive evaluation without the unassigned-variable check (callers check first).
function evalUnchecked(f, assignment) {
  switch (f.op) {
    case 'const':
      return Boolean(f.value);
    case 'var':
      return Boolean(assignment[f.name]);
    case 'not':
      return !evalUnchecked(f.operand, assignment);
    case 'and':
      return evalUnchecked(f.left, assignment) && evalUnchecked(f.right, assignment);
    case 'or':
      return evalUnchecked(f.left, assignment) || evalUnchecked(f.right, assignment);
    case 'implies':
      return !evalUnchecked(f.left, assignment) || evalUnchecked(f.right, assignment);
    case 'iff':
      return evalUnchecked(f.left, assignment) === evalUnchecked(f.right, assignment);
    default:
      throw new Error(`unknown op: ${String(f.op)}`);
  }
}

/** Two-valued evaluation; throws Error whose message contains the variable name if one is unassigned. */
export function evaluate(f, assignment) {
  for (const name of variables(f)) {
    if (!assignment || !Object.prototype.hasOwnProperty.call(assignment, name)) {
      throw new Error(`variable "${name}" is unassigned`);
    }
  }
  return evalUnchecked(f, assignment);
}

// All assignments over sorted names: first name slowest, false before true.
function allAssignments(names) {
  const n = names.length;
  const rows = [];
  for (let i = 0; i < 2 ** n; i++) {
    const a = {};
    for (let j = 0; j < n; j++) {
      a[names[j]] = Boolean((i >> (n - 1 - j)) & 1);
    }
    rows.push(a);
  }
  return rows;
}

/**
 * Array of satisfying assignments over `over` (default: variables(f)).
 * Order: names sorted (JS default string sort), false before true, first name varies slowest.
 * Each assignment object has exactly the names in `over` as keys.
 */
export function models(f, over) {
  const names = over === undefined
    ? variables(f)
    : [...new Set(over)].sort();
  return allAssignments(names).filter((a) => evaluate(f, a));
}

/** Array of {assignment, value} over variables(f) in the same order as models(). */
export function truthTable(f) {
  return allAssignments(variables(f)).map((assignment) => ({
    assignment,
    value: evaluate(f, assignment),
  }));
}

/** True iff every assignment satisfying all premises satisfies conclusion. */
export function entails(premises, conclusion) {
  const names = [...new Set([...premises, conclusion].flatMap((f) => variables(f)))].sort();
  for (const a of allAssignments(names)) {
    if (premises.every((p) => evalUnchecked(p, a)) && !evalUnchecked(conclusion, a)) {
      return false;
    }
  }
  return true;
}
