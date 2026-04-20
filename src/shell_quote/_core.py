"""Core quoting and splitting primitives for :mod:`shell_quote`."""

from __future__ import annotations

from typing import Iterable, List

__version__ = "1.0.0"

# Characters that are always safe to leave unquoted in a POSIX shell word.
# This is a deliberately conservative list; anything outside it triggers
# single-quote wrapping in :func:`quote`.
_ASCII_SAFE_PUNCT = frozenset("@%+=:,./-_")


class ShellQuoteError(ValueError):
    """Raised when :func:`split` cannot parse its input.

    Subclasses :class:`ValueError` so existing ``except ValueError`` handlers
    continue to catch it.
    """


def _require_str(value: object, name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(
            f"{name} must be a str, got {type(value).__name__}"
        )
    return value


def is_safe(value: str) -> bool:
    """Return ``True`` if *value* is safe as a bare POSIX shell word.

    An empty string is **not** considered safe because the shell would
    interpret the empty token as missing; :func:`quote` therefore wraps
    it as ``''``.

    Raises:
        TypeError: if *value* is not a string.
    """
    _require_str(value, "value")
    if not value:
        return False
    for char in value:
        if char.isalnum():
            continue
        if char in _ASCII_SAFE_PUNCT:
            continue
        if ord(char) >= 0x80:
            # Non-ASCII letters/marks are treated as literal bytes by
            # POSIX shells; they do not need quoting.
            continue
        return False
    return True


def quote(value: str) -> str:
    """Return *value* quoted so a POSIX shell passes it as one argument.

    Strategy:

    * Empty string becomes ``''``.
    * A string made entirely of *safe* characters is returned unchanged.
    * Otherwise the string is wrapped in single quotes, and each embedded
      ``'`` is replaced with ``'"'"'`` — the canonical break-out idiom
      recognised by every POSIX shell.

    Raises:
        TypeError: if *value* is not a string.
    """
    _require_str(value, "value")
    if not value:
        return "''"
    if is_safe(value):
        return value
    return "'" + value.replace("'", "'\"'\"'") + "'"


def quote_args(args: Iterable[str]) -> str:
    """Quote each string in *args* and join them with single spaces.

    Raises:
        TypeError: if *args* contains a non-string element.
    """
    return " ".join(quote(_require_str(a, "args element")) for a in args)


# --- split -----------------------------------------------------------------

_WHITESPACE = frozenset(" \t\n")
_DOUBLE_QUOTE_ESCAPES = frozenset('$`"\\')


def split(line: str) -> List[str]:
    """Parse *line* into argv-style tokens using POSIX shell rules.

    Supported syntax:

    * Unquoted whitespace (``space``, ``tab``, ``newline``) separates tokens.
    * ``'...'`` — literal, no escapes.
    * ``"..."`` — only ``\\$``, ``\\```, ``\\"``, ``\\\\``, and
      ``\\<newline>`` are recognised; other backslashes are literal.
    * Outside quotes, ``\\`` escapes the next character; ``\\<newline>``
      is a line continuation and disappears.
    * ``#`` starting a token begins a comment that runs to end-of-line.
    * Adjacent quoted and unquoted runs concatenate into one token
      (``"foo"'bar'baz`` → ``foobarbaz``).

    Variables (``$VAR``), command substitution (``$(...)`` / backticks),
    and globbing are **not** evaluated — they stay in the output as
    literal text.

    Raises:
        TypeError: if *line* is not a string.
        ShellQuoteError: on unterminated quotes or a trailing backslash.
    """
    _require_str(line, "line")

    tokens: List[str] = []
    current: List[str] = []
    token_started = False
    i = 0
    length = len(line)

    while i < length:
        char = line[i]

        # ---- whitespace ----
        if char in _WHITESPACE:
            if token_started:
                tokens.append("".join(current))
                current.clear()
                token_started = False
            i += 1
            continue

        # ---- comment ----
        if char == "#" and not token_started:
            while i < length and line[i] != "\n":
                i += 1
            continue

        # ---- single quote ----
        if char == "'":
            token_started = True
            i += 1
            end = line.find("'", i)
            if end == -1:
                raise ShellQuoteError("unterminated single quote")
            current.append(line[i:end])
            i = end + 1
            continue

        # ---- double quote ----
        if char == '"':
            token_started = True
            i += 1
            i = _consume_double_quoted(line, i, current)
            continue

        # ---- backslash (outside quotes) ----
        if char == "\\":
            if i + 1 >= length:
                raise ShellQuoteError("trailing backslash")
            nxt = line[i + 1]
            if nxt == "\n":
                # Line continuation — consume both characters.
                i += 2
                continue
            token_started = True
            current.append(nxt)
            i += 2
            continue

        # ---- ordinary character ----
        token_started = True
        current.append(char)
        i += 1

    if token_started:
        tokens.append("".join(current))
    return tokens


def _consume_double_quoted(line: str, start: int, out: List[str]) -> int:
    """Consume ``"..."`` starting at *start* (past the opening quote).

    Appends decoded characters to *out* and returns the index just after
    the closing ``"``.
    """
    i = start
    length = len(line)
    while i < length:
        char = line[i]
        if char == '"':
            return i + 1
        if char == "\\" and i + 1 < length:
            nxt = line[i + 1]
            if nxt == "\n":
                # Line continuation: both characters disappear.
                i += 2
                continue
            if nxt in _DOUBLE_QUOTE_ESCAPES:
                out.append(nxt)
                i += 2
                continue
            # Unknown escape — keep the backslash literally.
            out.append(char)
            i += 1
            continue
        out.append(char)
        i += 1
    raise ShellQuoteError("unterminated double quote")
