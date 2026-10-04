"""Tests for :mod:`open_llm_vtuber.utils.tts_preprocessor`.

These helpers clean the text that is sent to the TTS engine.  The cleaned text
never reaches the subtitles or the LLM memory, but a mistake here is audible, so
the filter behaviour is worth pinning down.
"""

from __future__ import annotations

import pytest

from open_llm_vtuber.utils import tts_preprocessor as tp


# --------------------------------------------------------------------------- #
# remove_special_characters
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Hello world!", "Hello world!"),
        ("Hello 😊!", "Hello !"),  # emoji (symbol category) are dropped
        ("你好，世界！", "你好,世界!"),  # NFKC turns full-width punctuation into ASCII
        ("①ＡＢ", "1AB"),  # NFKC normalisation
        ("e\u0301", "é"),  # a combining accent is normalised into a letter
        ("", ""),
    ],
)
def test_remove_special_characters(text, expected):
    assert tp.remove_special_characters(text) == expected


def test_remove_special_characters_keeps_letters_numbers_and_punctuation():
    text = "abc XYZ 123,.;:!?"
    assert tp.remove_special_characters(text) == text


def test_remove_special_characters_drops_control_characters():
    assert tp.remove_special_characters("a\x00\x07b") == "ab"


# --------------------------------------------------------------------------- #
# Nested symbol filters
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    ("func", "text", "expected"),
    [
        (tp.filter_brackets, "a[b[c]d]e", "ae"),
        (tp.filter_brackets, "keep [drop] end", "keep end"),
        (tp.filter_brackets, "no brackets", "no brackets"),
        (tp.filter_parentheses, "a (b (c) d) e", "a e"),
        (tp.filter_parentheses, "no parens", "no parens"),
        (tp.filter_angle_brackets, "a<b>c", "ac"),
        (tp.filter_angle_brackets, "no angles", "no angles"),
    ],
)
def test_nested_filters_remove_matched_regions(func, text, expected):
    assert func(text) == expected


def test_filters_collapse_extra_whitespace():
    assert tp.filter_brackets("keep   [drop]   this") == "keep this"
    assert tp.filter_parentheses("a  (b)  c") == "a c"


def test_filter_brackets_keeps_unbalanced_text_after_the_bracket():
    # An unclosed '[' opens a region that is never closed: the rest is dropped.
    assert tp.filter_brackets("unbalanced [abc") == "unbalanced"


def test_full_width_parentheses_are_not_removed():
    assert tp.filter_parentheses("（全角）hello") == "（全角）hello"


def test_nested_filters_reject_non_string_input():
    with pytest.raises(TypeError):
        tp._filter_nested(None, "[", "]")


# --------------------------------------------------------------------------- #
# filter_asterisks
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("*smiles* hello", "hello"),
        ("**bold** text", "text"),
        ("a *b* c *d* e", "a c e"),
        ("no asterisks", "no asterisks"),
    ],
)
def test_filter_asterisks(text, expected):
    assert tp.filter_asterisks(text) == expected


def test_filter_asterisks_keeps_unclosed_asterisk():
    assert tp.filter_asterisks("*unclosed") == "*unclosed"


# --------------------------------------------------------------------------- #
# tts_filter
# --------------------------------------------------------------------------- #
def test_tts_filter_with_every_option_disabled_returns_the_text_unchanged():
    text = "[a] *b* (c) <d> 你好!"
    assert tp.tts_filter(text, False, False, False, False, False) == text


def test_tts_filter_with_every_option_enabled_removes_all_marked_text():
    assert (
        tp.tts_filter("[a] *b* (c) <d> 你好!", True, True, True, True, True) == "你好!"
    )


def test_tts_filter_only_applies_the_requested_filters():
    # ignore_asterisks only
    assert tp.tts_filter("[a] *b* (c)", False, False, False, True, False) == "[a] (c)"
    # remove_special_char returns the text unchanged here, so it must stay untouched
    assert tp.tts_filter("plain text", True, False, False, False, False) == "plain text"


def test_tts_filter_handles_empty_text():
    assert tp.tts_filter("", True, True, True, True, True) == ""


def test_tts_filter_uses_the_translator_when_provided():
    class Translator:
        def translate(self, text: str) -> str:
            return f"<translated>{text}"

    assert tp.tts_filter("Hello", False, False, False, False, False, Translator()) == (
        "<translated>Hello"
    )


def test_tts_filter_falls_back_to_the_original_text_when_translation_fails():
    class BrokenTranslator:
        def translate(self, text: str) -> str:
            raise RuntimeError("boom")

    assert (
        tp.tts_filter("Hello", False, False, False, False, False, BrokenTranslator())
        == "Hello"
    )


def test_tts_filter_returns_the_text_when_a_filter_raises(monkeypatch):
    def boom(text):
        raise RuntimeError("boom")

    monkeypatch.setattr(tp, "filter_brackets", boom)
    assert (
        tp.tts_filter("keep [me] please", False, True, False, False, False)
        == "keep [me] please"
    )
