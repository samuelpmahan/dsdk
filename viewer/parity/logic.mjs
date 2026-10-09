// Independent JS counterpart of dsdk.logic (A1), used for B3 Python/JS parity.
// It shares no code with the Python side; the shared JSON fixtures are the only contract.
// Formula encoding = the fixtures' "structure" objects:
//   {op:"const",value}, {op:"var",name}, {op:"not",operand},
//   {op:"and"|"or"|"implies"|"iff", left, right}

/** Canonical fully-parenthesised string; must equal the fixture "string" field. */
export function toStr(f) { throw new Error('not implemented'); }

/** Sorted array of distinct variable names. */
export function variables(f) { throw new Error('not implemented'); }

/** Node count (every const/var/not/binary node counts 1). */
export function size(f) { throw new Error('not implemented'); }

/** Two-valued evaluation; throws Error whose message contains the variable name if one is unassigned. */
export function evaluate(f, assignment) { throw new Error('not implemented'); }

/**
 * Array of satisfying assignments over `over` (default: variables(f)).
 * Order: names sorted (JS default string sort), false before true, first name varies slowest.
 * Each assignment object has exactly the names in `over` as keys.
 */
export function models(f, over) { throw new Error('not implemented'); }

/** Array of {assignment, value} over variables(f) in the same order as models(). */
export function truthTable(f) { throw new Error('not implemented'); }

/** True iff every assignment satisfying all premises satisfies conclusion. */
export function entails(premises, conclusion) { throw new Error('not implemented'); }
