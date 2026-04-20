"""Tests for :func:`shell_quote.split`."""

from __future__ import annotations

import pytest

from shell_quote import ShellQuoteError, quote_args, split


class TestSplitHappyPath:
    def test_split_empty_string(self) -> None:
        assert split("") == []

    def test_split_only_whitespace(self) -> None:
        assert split("   \t  \n  ") == []

    def test_split_single_word(self) -> None:
        assert split("hello") == ["hello"]

    def test_split_two_words(self) -> None:
        assert split("hello world") == ["hello", "world"]

    def test_split_collapses_multiple_spaces(self) -> None:
        assert split("hello    world") == ["hello", "world"]

    def test_split_strips_leading_trailing_whitespace(self) -> None:
        assert split("  hello world  ") == ["hello", "world"]

    def test_split_handles_tabs_and_newlines_as_whitespace(self) -> None:
        assert split("a\tb\nc") == ["a", "b", "c"]


class TestSplitSingleQuotes:
    def test_split_single_quoted_preserves_spaces(self) -> None:
        assert split("'hello world'") == ["hello world"]

    def test_split_single_quoted_preserves_specials(self) -> None:
        assert split("'$HOME `date` \"foo\"'") == ['$HOME `date` "foo"']

    def test_split_empty_single_quotes_is_empty_arg(self) -> None:
        assert split("''") == [""]

    def test_split_backslash_inside_single_quotes_is_literal(self) -> None:
        # Inside '...', backslash has no special meaning.
        assert split(r"'a\b'") == [r"a\b"]

    def test_split_unterminated_single_quote_raises(self) -> None:
        with pytest.raises(ShellQuoteError, match="unterminated single quote"):
            split("'hello")


class TestSplitDoubleQuotes:
    def test_split_double_quoted_preserves_spaces(self) -> None:
        assert split('"hello world"') == ["hello world"]

    def test_split_double_quoted_empty_is_empty_arg(self) -> None:
        assert split('""') == [""]

    def test_split_double_quoted_escape_dollar(self) -> None:
        # \$ is a recognised escape inside double quotes.
        assert split(r'"\$HOME"') == ["$HOME"]

    def test_split_double_quoted_escape_backtick(self) -> None:
        assert split(r'"\`date\`"') == ["`date`"]

    def test_split_double_quoted_escape_backslash(self) -> None:
        assert split(r'"a\\b"') == [r"a\b"]

    def test_split_double_quoted_escape_double_quote(self) -> None:
        assert split(r'"a\"b"') == ['a"b']

    def test_split_double_quoted_unrecognised_escape_kept_literal(self) -> None:
        # Per POSIX, only $ ` " \ and <newline> are recognised inside "...".
        # Other \x sequences keep the backslash.
        assert split(r'"a\nb"') == [r"a\nb"]

    def test_split_double_quoted_line_continuation(self) -> None:
        assert split('"hello\\\nworld"') == ["helloworld"]

    def test_split_unterminated_double_quote_raises(self) -> None:
        with pytest.raises(ShellQuoteError, match="unterminated double quote"):
            split('"hello')


class TestSplitBackslashOutsideQuotes:
    def test_split_backslash_escapes_space(self) -> None:
        assert split(r"hello\ world") == ["hello world"]

    def test_split_backslash_escapes_dollar(self) -> None:
        assert split(r"\$HOME") == ["$HOME"]

    def test_split_backslash_line_continuation_outside_quotes(self) -> None:
        assert split("hello\\\nworld") == ["helloworld"]

    def test_split_trailing_backslash_raises(self) -> None:
        with pytest.raises(ShellQuoteError, match="trailing backslash"):
            split("abc\\")


class TestSplitConcatenation:
    def test_split_adjacent_quoted_and_unquoted_concatenate(self) -> None:
        # POSIX semantics: quotes do not break a token unless whitespace intervenes.
        assert split('"foo"\'bar\'baz') == ["foobarbaz"]

    def test_split_quote_in_middle_of_word(self) -> None:
        assert split("a'b c'd") == ["ab cd"]

    def test_split_empty_quotes_produce_empty_only_when_alone(self) -> None:
        assert split("a''b") == ["ab"]
        assert split("''") == [""]


class TestSplitComments:
    def test_split_hash_at_token_start_is_comment(self) -> None:
        assert split("cmd arg # a comment") == ["cmd", "arg"]

    def test_split_hash_mid_token_is_literal(self) -> None:
        assert split("abc#def") == ["abc#def"]

    def test_split_comment_spans_to_end_of_line(self) -> None:
        assert split("cmd # ignored stuff\nmore") == ["cmd", "more"]

    def test_split_hash_inside_quotes_is_literal(self) -> None:
        assert split("'#hash'") == ["#hash"]


class TestSplitTypes:
    def test_split_rejects_non_string(self) -> None:
        with pytest.raises(TypeError):
            split(42)  # type: ignore[arg-type]

    def test_split_rejects_bytes(self) -> None:
        with pytest.raises(TypeError):
            split(b"foo")  # type: ignore[arg-type]


class TestSplitQuoteRoundTrip:
    @pytest.mark.parametrize(
        "args",
        [
            [],
            ["hello"],
            ["hello", "world"],
            ["a b", "c d"],
            ["$HOME", "`date`"],
            ["it's", "a 'test'"],
            ["*.py", "?", "[abc]"],
            ["line1\nline2", "tab\there"],
            ["\x00", "bell\x07"],
            ["--flag=value with space"],
        ],
    )
    def test_round_trip_quote_args_then_split(self, args: list[str]) -> None:
        reencoded = quote_args(args)
        assert split(reencoded) == args
