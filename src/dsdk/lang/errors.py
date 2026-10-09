"""Error types shared by the lexer and both parsers (fully implemented; not a task).

* ``LangError(message, offset)`` -- base class. ``.offset`` is a 0-based index into the input ``str`` (a code-point
  index, not a byte index) and ``.message`` is the human text. ``str(e)`` includes both.
* ``LexError`` -- raised by the tokenizer for a character that cannot start or continue any token.
* ``ParseError(message, offset, expected)`` -- raised by the parsers. ``.expected`` is a ``frozenset[str]`` of TOKEN KIND
  names (see :mod:`dsdk.lang.lexer`) plus the pseudo-kind ``"END"`` (end of input) that would have been accepted at
  ``offset`` instead of what was found.
"""
from __future__ import annotations


class LangError(Exception):
    """Base class: something is wrong with the input text at ``offset``."""

    def __init__(self, message: str, offset: int) -> None:
        super().__init__(f"{message} (at offset {offset})")
        self.message = message
        self.offset = offset


class LexError(LangError):
    """A character that cannot be tokenized. ``offset`` is the index of that character."""


class ParseError(LangError):
    """Tokens that do not fit the grammar. ``offset`` is the START of the first offending token, or ``len(text)`` when
    the input ended too early; ``expected`` says what would have been acceptable there."""

    def __init__(self, message: str, offset: int, expected=frozenset()) -> None:
        super().__init__(message, offset)
        self.expected: frozenset[str] = frozenset(expected)
