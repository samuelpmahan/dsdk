"""Test-only helpers for tests/lang: strategies, a tiny INDEPENDENT reader/printer for canonical Calc source, and oracles.

Named ``lang_helpers`` (not ``helpers``) because pytest puts each tests/<pkg>/ directory on sys.path and tests/logic already
owns the module name ``helpers``. Uses only the public dsdk API and constructors; the reader/printer/evaluator below are
deliberately naive and do NOT use dsdk.lang.calc.parse_calc / to_source / step / evaluate, so that tasks can be implemented
and tested independently of each other.
"""
import json
import re
from pathlib import Path

from hypothesis import strategies as st

from dsdk.lang.calc import OPS, BinOp, BoolLit, If, IntLit, Let, Not, Type, Var
from dsdk import logic

FIXDIR = Path(__file__).resolve().parents[2] / "fixtures" / "lang"
NAMES = ["x", "y", "z"]


# ----------------------------------------------------------------------------- canonical reader / printer (oracle)
def T(src):
    """Read CANONICAL (fully parenthesised) Calc source into an Expr: ``(1 + 2)``, ``(not b)``, ``(if c then t else e)``,
    ``(let x = e in e)``, literals ``3`` ``-3`` ``true`` ``false``, variables. No precedence, no extra parentheses."""
    toks = re.findall(r"\(|\)|[^\s()]+", src)
    pos = 0

    def nxt():
        nonlocal pos
        pos += 1
        return toks[pos - 1]

    def expect(t):
        got = nxt()
        assert got == t, f"expected {t!r} got {got!r} in {src!r}"

    def go():
        t = nxt()
        if t == "true" or t == "false":
            return BoolLit(t == "true")
        if re.fullmatch(r"-?[0-9]+", t):
            return IntLit(int(t))
        if t != "(":
            return Var(t)
        head = toks[pos]
        if head == "not":
            nxt()
            e = go()
            expect(")")
            return Not(e)
        if head == "if":
            nxt()
            c = go()
            expect("then")
            a = go()
            expect("else")
            b = go()
            expect(")")
            return If(c, a, b)
        if head == "let":
            nxt()
            name = nxt()
            expect("=")
            b = go()
            expect("in")
            body = go()
            expect(")")
            return Let(name, b, body)
        left = go()
        op = nxt()
        assert op in OPS, f"bad operator {op!r} in {src!r}"
        right = go()
        expect(")")
        return BinOp(op, left, right)

    out = go()
    assert pos == len(toks), f"trailing tokens in {src!r}"
    return out


def show(e):
    """Canonical source of an Expr, independent of dsdk.lang.calc.to_source."""
    if isinstance(e, IntLit):
        return str(e.value)
    if isinstance(e, BoolLit):
        return "true" if e.value else "false"
    if isinstance(e, Var):
        return e.name
    if isinstance(e, BinOp):
        return f"({show(e.left)} {e.op} {show(e.right)})"
    if isinstance(e, Not):
        return f"(not {show(e.operand)})"
    if isinstance(e, If):
        return f"(if {show(e.cond)} then {show(e.then)} else {show(e.orelse)})"
    return f"(let {e.name} = {show(e.bound)} in {show(e.body)})"


# ----------------------------------------------------------------------------- environment-based oracle evaluator
class OracleStuck(Exception):
    pass


def oracle_eval(e, env=None):
    """Environment-passing (NOT substitution) evaluator for the same call-by-value, short-circuit semantics. Raises
    OracleStuck. Written separately from dsdk.lang.calc.evaluate on purpose."""
    env = env or {}
    if isinstance(e, (IntLit, BoolLit)):
        return e.value
    if isinstance(e, Var):
        if e.name not in env:
            raise OracleStuck(e.name)
        return env[e.name]
    if isinstance(e, Not):
        v = oracle_eval(e.operand, env)
        if type(v) is not bool:
            raise OracleStuck("not")
        return not v
    if isinstance(e, If):
        c = oracle_eval(e.cond, env)
        if type(c) is not bool:
            raise OracleStuck("if")
        return oracle_eval(e.then if c else e.orelse, env)
    if isinstance(e, Let):
        v = oracle_eval(e.bound, env)
        new = dict(env)
        new[e.name] = v
        return oracle_eval(e.body, new)
    a = oracle_eval(e.left, env)
    if e.op == "and":
        if type(a) is not bool:
            raise OracleStuck("and")
        return oracle_eval(e.right, env) if a else False
    if e.op == "or":
        if type(a) is not bool:
            raise OracleStuck("or")
        return True if a else oracle_eval(e.right, env)
    b = oracle_eval(e.right, env)
    if type(a) is int and type(b) is int:
        return {"+": a + b, "-": a - b, "*": a * b, "<": a < b, "==": a == b}[e.op]
    if e.op == "==" and type(a) is bool and type(b) is bool:
        return a == b
    raise OracleStuck(e.op)


# ----------------------------------------------------------------------------- builders for deep terms
def right_sum(n):
    """1 + (1 + (... + 1)) with n additions (depth n, size 2n+1)."""
    e = IntLit(1)
    for _ in range(n):
        e = BinOp("+", IntLit(1), e)
    return e


def left_sum(n):
    e = IntLit(1)
    for _ in range(n):
        e = BinOp("+", e, IntLit(1))
    return e


# ----------------------------------------------------------------------------- Hypothesis strategies
def any_exprs(max_leaves=10):
    """Arbitrary (usually ill-typed or open) Calc trees: exercises stuck terms."""
    leaf = st.integers(-3, 5).map(IntLit) | st.booleans().map(BoolLit) | st.sampled_from(NAMES).map(Var)
    return st.recursive(
        leaf,
        lambda c: (
            st.builds(BinOp, st.sampled_from(OPS), c, c)
            | c.map(Not)
            | st.builds(If, c, c, c)
            | st.builds(Let, st.sampled_from(NAMES), c, c)
        ),
        max_leaves=max_leaves,
    )


@st.composite
def _typed(draw, ty, env, depth):
    names_of_ty = [n for n, t in env if t is ty]
    options = ["lit", "if", "let"] if depth > 0 else ["lit"]
    if names_of_ty:
        options.append("var")
    if depth > 0:
        options += ["arith", "arith"] if ty is Type.INT else ["cmp", "eqb", "logic", "not"]
    kind = draw(st.sampled_from(options))
    sub = lambda t, e=env: _typed(t, e, depth - 1)  # noqa: E731
    if kind == "lit":
        return IntLit(draw(st.integers(-4, 6))) if ty is Type.INT else BoolLit(draw(st.booleans()))
    if kind == "var":
        return Var(draw(st.sampled_from(names_of_ty)))
    if kind == "arith":
        return BinOp(draw(st.sampled_from(["+", "-", "*"])), draw(sub(Type.INT)), draw(sub(Type.INT)))
    if kind == "cmp":
        return BinOp(draw(st.sampled_from(["<", "=="])), draw(sub(Type.INT)), draw(sub(Type.INT)))
    if kind == "eqb":
        return BinOp("==", draw(sub(Type.BOOL)), draw(sub(Type.BOOL)))
    if kind == "logic":
        return BinOp(draw(st.sampled_from(["and", "or"])), draw(sub(Type.BOOL)), draw(sub(Type.BOOL)))
    if kind == "not":
        return Not(draw(sub(Type.BOOL)))
    if kind == "if":
        return If(draw(sub(Type.BOOL)), draw(sub(ty)), draw(sub(ty)))
    name = draw(st.sampled_from(NAMES))
    t1 = draw(st.sampled_from([Type.INT, Type.BOOL]))
    bound = draw(sub(t1))
    new_env = tuple(sorted({**dict(env), name: t1}.items(), key=lambda kv: kv[0]))
    return Let(name, bound, draw(_typed(ty, new_env, depth - 1)))


def typed_exprs(ty, env=(), depth=3):
    """Well-typed Calc trees of type ``ty`` under ``env`` (an iterable of (name, Type)); closed if env is empty."""
    return _typed(ty, tuple(sorted(dict(env).items())), depth)


closed_typed = st.sampled_from([Type.INT, Type.BOOL]).flatmap(lambda t: typed_exprs(t).map(lambda e: (t, e)))


def formulas(names=("a", "b", "c"), max_leaves=8):
    leaf = st.sampled_from(names).map(logic.Var) | st.booleans().map(logic.Const)
    return st.recursive(
        leaf,
        lambda c: (
            c.map(logic.Not)
            | st.builds(logic.And, c, c)
            | st.builds(logic.Or, c, c)
            | st.builds(logic.Implies, c, c)
            | st.builds(logic.Iff, c, c)
        ),
        max_leaves=max_leaves,
    )


# ----------------------------------------------------------------------------- minimal-parentheses formula printer (oracle)
_PREC = {logic.Iff: 1, logic.Implies: 2, logic.Or: 3, logic.And: 4, logic.Not: 5}
_SYM = {logic.Iff: "<->", logic.Implies: "->", logic.Or: "|", logic.And: "&"}
_LEFT_ASSOC = {logic.Iff: True, logic.Implies: False, logic.Or: True, logic.And: True}


def _pieces(f):
    """Token pieces of ``f`` with the FEWEST parentheses that parse back to ``f`` under the documented relaxed grammar."""
    if isinstance(f, logic.Const):
        return ["true" if f.value else "false"]
    if isinstance(f, logic.Var):
        return [f.name]
    if isinstance(f, logic.Not):
        inner = _pieces(f.operand)
        return ["~"] + (inner if _PREC.get(type(f.operand), 9) >= 5 else ["("] + inner + [")"])
    cls = type(f)
    out = []
    for side, child in (("l", f.left), ("r", f.right)):
        p = _PREC.get(type(child), 9)
        same_side_ok = (side == "l") == _LEFT_ASSOC[cls]
        needs = p < _PREC[cls] or (p == _PREC[cls] and not same_side_ok)
        out += (["("] + _pieces(child) + [")"]) if needs else _pieces(child)
        if side == "l":
            out.append(_SYM[cls])
    return out


def relaxed_text(f, spacing):
    """Minimal-paren text of ``f``; ``spacing`` is a list of whitespace strings used cyclically between pieces. Two adjacent
    names/keywords always get at least one space (they never are adjacent: operators separate them)."""
    pieces = _pieces(f)
    out = []
    for i, p in enumerate(pieces):
        out.append(p)
        if i + 1 < len(pieces):
            out.append(spacing[i % len(spacing)])
    return "".join(out)


# ----------------------------------------------------------------------------- JSON AST encoding (see fixtures/lang/calc_programs.json)
def encode_ast(e):
    if isinstance(e, IntLit):
        return {"t": "int", "v": str(e.value)}
    if isinstance(e, BoolLit):
        return {"t": "bool", "v": e.value}
    if isinstance(e, Var):
        return {"t": "var", "name": e.name}
    if isinstance(e, BinOp):
        return {"t": "bin", "op": e.op, "l": encode_ast(e.left), "r": encode_ast(e.right)}
    if isinstance(e, Not):
        return {"t": "not", "e": encode_ast(e.operand)}
    if isinstance(e, If):
        return {"t": "if", "c": encode_ast(e.cond), "th": encode_ast(e.then), "el": encode_ast(e.orelse)}
    return {"t": "let", "name": e.name, "bound": encode_ast(e.bound), "body": encode_ast(e.body)}


def decode_ast(d):
    t = d["t"]
    if t == "int":
        return IntLit(int(d["v"]))
    if t == "bool":
        return BoolLit(d["v"])
    if t == "var":
        return Var(d["name"])
    if t == "bin":
        return BinOp(d["op"], decode_ast(d["l"]), decode_ast(d["r"]))
    if t == "not":
        return Not(decode_ast(d["e"]))
    if t == "if":
        return If(decode_ast(d["c"]), decode_ast(d["th"]), decode_ast(d["el"]))
    return Let(d["name"], decode_ast(d["bound"]), decode_ast(d["body"]))


def load_fixture(name):
    return json.loads((FIXDIR / name).read_text(encoding="utf-8"))
