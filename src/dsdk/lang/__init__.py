"""dsdk.lang (track A2): tokenizer DFA, formula parser, the typed Calc language, and bridges to earlier tracks.

Builds on dsdk.logic (formula_syntax returns logic Formulas; bridge embeds them into Calc and checks against
``logic.evaluate``) and dsdk.core (calc.typecheck returns a Judgment; bridge records evaluation traces as PxC Parts).
"""
from . import bridge, calc, errors, formula_syntax, lexer
from .errors import LangError, LexError, ParseError
from .formula_syntax import all_parses, parse_formula
from .lexer import Token, tokenize

__all__ = [
    "LangError", "LexError", "ParseError", "Token", "all_parses", "bridge", "calc", "errors",
    "formula_syntax", "lexer", "parse_formula", "tokenize",
]
