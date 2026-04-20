"""Tests for :func:`shell_quote.quote` and :func:`shell_quote.quote_args`."""

from __future__ import annotations

import subprocess
import sys

import pytest

from shell_quote import is_safe, quote, quote_args


class TestQuoteHappyPath:
    def test_quote_empty_string_becomes_empty_single_quoted_pair(self) -> None:
        assert quote("") == "''"

    def test_quote_simple_word_unchanged(self) -> None:
        assert quote("hello") == "hello"

    def test_quote_alphanumeric_unchanged(self) -> None:
        assert quote("abc123") == "abc123"

    def test_quote_safe_punct_unchanged(self) -> None:
        assert quote("path/to/file_1.txt") == "path/to/file_1.txt"

    def test_quote_safe_symbols_unchanged(self) -> None:
        for safe in ("foo@bar", "a%b", "x+y", "key=value", "k:v", "a,b", "./rel"):
            assert quote(safe) == safe

    def test_quote_dash_prefixed_token_unchanged(self) -> None:
        assert quote("--verbose") == "--verbose"


class TestQuoteNeedsEscaping:
    def test_quote_space_gets_wrapped_in_single_quotes(self) -> None:
        assert quote("hello world") == "'hello world'"

    def test_quote_dollar_sign_prevented_from_expansion(self) -> None:
        assert quote("$HOME") == "'$HOME'"

    def test_quote_backtick_prevented_from_command_sub(self) -> None:
        assert quote("`date`") == "'`date`'"

    def test_quote_double_quote_character_wrapped(self) -> None:
        assert quote('say "hi"') == "'say \"hi\"'"

    def test_quote_glob_chars_wrapped(self) -> None:
        assert quote("*.py") == "'*.py'"
        assert quote("?") == "'?'"
        assert quote("[abc]") == "'[abc]'"

    def test_quote_newline_forces_single_quote(self) -> None:
        assert quote("line1\nline2") == "'line1\nline2'"

    def test_quote_tab_forces_single_quote(self) -> None:
        assert quote("a\tb") == "'a\tb'"

    def test_quote_semicolon_forces_single_quote(self) -> None:
        assert quote("a;b") == "'a;b'"

    def test_quote_pipe_forces_single_quote(self) -> None:
        assert quote("a|b") == "'a|b'"

    def test_quote_ampersand_forces_single_quote(self) -> None:
        assert quote("a&b") == "'a&b'"

    def test_quote_redirect_forces_single_quote(self) -> None:
        assert quote("a>b") == "'a>b'"
        assert quote("a<b") == "'a<b'"

    def test_quote_parens_force_single_quote(self) -> None:
        assert quote("(a)") == "'(a)'"

    def test_quote_braces_force_single_quote(self) -> None:
        assert quote("{a,b}") == "'{a,b}'"

    def test_quote_single_quote_uses_break_out_idiom(self) -> None:
        # The canonical POSIX idiom: end the '..' string, type a literal
        # '"'"' for the quote, resume the '..' string.
        assert quote("it's") == """'it'"'"'s'"""

    def test_quote_only_single_quote_becomes_literal(self) -> None:
        assert quote("'") == """''"'"''"""

    def test_quote_multiple_single_quotes(self) -> None:
        assert quote("a'b'c") == """'a'"'"'b'"'"'c'"""

    def test_quote_unicode_alnum_kept_safe(self) -> None:
        # Unicode letters and digits should pass through unquoted — POSIX
        # shells treat bytes outside ASCII as regular literals.
        assert quote("héllo") == "héllo"
        assert quote("漢字") == "漢字"

    def test_quote_unicode_non_alnum_symbols_kept_safe(self) -> None:
        # Non-ASCII non-alphanumerics (emoji, em-dash, curly quote) fall
        # through the ord >= 0x80 branch and stay unquoted. Shells
        # don't assign them any special meaning.
        assert quote("—") == "—"
        assert quote("👋") == "👋"

    def test_quote_control_chars_force_single_quote(self) -> None:
        assert quote("\x00") == "'\x00'"
        assert quote("bell\x07here") == "'bell\x07here'"


class TestQuoteTypes:
    def test_quote_rejects_non_string(self) -> None:
        with pytest.raises(TypeError):
            quote(42)  # type: ignore[arg-type]

    def test_quote_rejects_none(self) -> None:
        with pytest.raises(TypeError):
            quote(None)  # type: ignore[arg-type]

    def test_quote_rejects_bytes(self) -> None:
        with pytest.raises(TypeError):
            quote(b"hello")  # type: ignore[arg-type]


class TestQuoteArgs:
    def test_quote_args_joins_with_spaces(self) -> None:
        assert quote_args(["ls", "-la"]) == "ls -la"

    def test_quote_args_quotes_each_arg(self) -> None:
        assert quote_args(["echo", "hello world"]) == "echo 'hello world'"

    def test_quote_args_empty_iterable(self) -> None:
        assert quote_args([]) == ""

    def test_quote_args_tuple_input(self) -> None:
        assert quote_args(("a", "b c")) == "a 'b c'"

    def test_quote_args_generator_input(self) -> None:
        def gen():
            yield "a"
            yield "b c"

        assert quote_args(gen()) == "a 'b c'"

    def test_quote_args_rejects_non_string_element(self) -> None:
        with pytest.raises(TypeError):
            quote_args(["ls", 42])  # type: ignore[list-item]


class TestIsSafe:
    def test_is_safe_non_empty_alnum(self) -> None:
        assert is_safe("abc") is True

    def test_is_safe_empty_is_false(self) -> None:
        # Empty needs the `''` quoting.
        assert is_safe("") is False

    def test_is_safe_space_is_false(self) -> None:
        assert is_safe("a b") is False

    def test_is_safe_rejects_non_string(self) -> None:
        with pytest.raises(TypeError):
            is_safe(123)  # type: ignore[arg-type]


@pytest.mark.skipif(sys.platform == "win32", reason="needs /bin/sh")
class TestRoundTripWithRealShell:
    """Hand our quoted output to a real POSIX shell and verify it round-trips."""

    @staticmethod
    def _echo(value: str) -> str:
        cmd = "printf '%s' " + quote(value)
        result = subprocess.run(
            ["/bin/sh", "-c", cmd],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout

    def test_round_trip_with_dollar_sign(self) -> None:
        assert self._echo("$HOME and $PATH") == "$HOME and $PATH"

    def test_round_trip_with_backtick(self) -> None:
        assert self._echo("`date`") == "`date`"

    def test_round_trip_with_single_quote(self) -> None:
        assert self._echo("it's a test") == "it's a test"

    def test_round_trip_with_newline(self) -> None:
        assert self._echo("line1\nline2") == "line1\nline2"

    def test_round_trip_with_glob(self) -> None:
        assert self._echo("*.py") == "*.py"
