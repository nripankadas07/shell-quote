"""shell_quote — zero-dependency POSIX shell quoting and splitting.

Public API:

* :func:`quote` — quote a single string so POSIX ``/bin/sh`` treats it
  as one literal argument.
* :func:`quote_args` — quote each item in an iterable and join them
  with spaces.
* :func:`split` — parse a quoted shell command string into its argument
  list (the inverse of :func:`quote_args`).
* :func:`is_safe` — check whether a string needs any quoting at all.
* :class:`ShellQuoteError` — raised by :func:`split` for malformed input.

The implementation follows the POSIX 1003.1 "Shell Command Language"
rules for single quotes, double quotes, and backslash escapes. It does
not evaluate variables, backticks, or globs — it is purely
lexical.
"""

from __future__ import annotations

from ._core import (
    ShellQuoteError,
    __version__,
    is_safe,
    quote,
    quote_args,
    split,
)

__all__ = [
    "ShellQuoteError",
    "__version__",
    "is_safe",
    "quote",
    "quote_args",
    "split",
]
