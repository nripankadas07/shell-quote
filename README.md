# shell-quote

Zero-dependency POSIX shell quoting, splitting, and safety checks for
Python. A small, auditable replacement for the relevant bits of
`shlex` with clearer errors, stricter rules, and a lossless
`quote_args`/`split` round-trip.

Why roll this when the standard library already ships `shlex.quote`
and `shlex.split`?

- `shlex.quote` wraps every string in single quotes, even obviously
  safe ones like `ls`. This one does not.
- `shlex.split` silently accepts malformed input in some edge cases;
  this one raises `ShellQuoteError`.
- Clear, documented rules. No posix-mode/non-posix-mode toggles.

## Install

```bash
pip install shell-quote
```

Requires Python 3.8 or newer. Zero runtime dependencies.

## Usage

```python
from shell_quote import quote, quote_args, split, is_safe

# Quote a single string
quote("hello")          # 'hello'          (safe, unchanged)
quote("hello world")    # "'hello world'"
quote("it's")           # "'it'\"'\"'s'"   (canonical POSIX break-out)

# Build a full command line
cmd = quote_args(["ssh", "user@host", "echo", "$HOME is mine"])
# => ssh user@host echo '$HOME is mine'

# Parse one back apart
split("ssh user@host echo '$HOME is mine'")
# => ['ssh', 'user@host', 'echo', '$HOME is mine']

# Ask whether a string needs quoting at all
is_safe("path/to/file")  # True
is_safe("a b")            # False
```

### Round-tripping

`split(quote_args(args)) == args` holds for any list of strings —
including ones containing spaces, `$`, backticks, newlines, glob
characters, and single quotes.

## API reference

### `quote(value: str) -> str`

Return `value` quoted so a POSIX shell (`/bin/sh`, `bash`, `dash`,
`zsh`, `ksh`, `ash`, …) treats it as one literal argument.

- Empty string → `"''"`.
- All-safe strings are returned unchanged.
- Everything else is wrapped in `'...'`, with embedded `'` replaced
  by `'"'"'`.

Raises `TypeError` on non-string input.

### `quote_args(args: Iterable[str]) -> str`

Apply `quote` to each element and join with a single space.

### `split(line: str) -> list[str]`

Parse `line` into argv-style tokens. Supports:

- Unquoted whitespace separates tokens.
- `'...'` — literal, no escapes.
- `"..."` — only `\$`, `` \` ``, `\"`, `\\`, and `\<newline>` are
  recognised escapes; other `\x` sequences keep the backslash.
- Outside quotes, `\` escapes the next character; `\<newline>` is a
  line continuation.
- `#` at the start of a token begins a comment that runs to end of
  line.
- Adjacent quoted + unquoted runs concatenate into one token, so
  `"foo"'bar'baz` → `foobarbaz`.

Variables (`$VAR`), command substitution, and globbing are **not**
expanded — they stay in the output as literal text. The split is
purely lexical.

Raises `ShellQuoteError` on unterminated quotes or a trailing
backslash; `TypeError` on non-string input.

### `is_safe(value: str) -> bool`

`True` when `value` contains only characters that a POSIX shell will
pass through unchanged (alphanumerics, `@%+=:,./-_`, and any
non-ASCII byte). Empty strings are not safe — they need `''`
quoting.

### `ShellQuoteError`

Subclass of `ValueError` raised by `split` for malformed input.

## Running tests

```bash
pip install -e '.[dev]'
pytest
pytest --cov=shell_quote --cov-report=term-missing
```

The suite includes a round-trip against a real `/bin/sh` (skipped on
Windows) to make sure what `quote` produces is what the shell gives
back.

## License

MIT.
