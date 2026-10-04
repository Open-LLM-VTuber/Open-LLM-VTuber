"""Tests for :mod:`open_llm_vtuber.utils.sentence_divider`.

The divider sits between an LLM token stream and the TTS engine: it turns
incremental text chunks into complete sentences (and ``<think>``-style tag
boundaries).  Everything in this module is pure text processing, so no model,
network access or audio device is required.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from open_llm_vtuber.utils import sentence_divider as sd
from open_llm_vtuber.utils.sentence_divider import (
    SUPPORTED_LANGUAGES,
    SentenceDivider,
    SentenceWithTags,
    TagState,
    comma_splitter,
    contains_comma,
    contains_end_punctuation,
    detect_language,
    has_punctuation,
    is_complete_sentence,
    segment_text_by_pysbd,
    segment_text_by_regex,
)


async def _chunk_stream(chunks: list[Any]):
    for chunk in chunks:
        yield chunk


async def _collect(
    chunks: list[Any], divider: SentenceDivider | None = None, **kwargs: Any
):
    divider = divider or SentenceDivider(**kwargs)
    items = [item async for item in divider.process_stream(_chunk_stream(chunks))]
    return divider, items


def process(chunks: list[Any], **kwargs: Any):
    """Feed ``chunks`` through a fresh divider and return ``(divider, items)``."""
    return asyncio.run(_collect(chunks, **kwargs))


def process_with(divider: SentenceDivider, chunks: list[Any]):
    """Feed ``chunks`` through an existing divider, keeping its state."""
    return asyncio.run(_collect(chunks, divider=divider))


def texts(items: list[Any]) -> list[str]:
    return [item.text for item in items if isinstance(item, SentenceWithTags)]


def tag_states(item: SentenceWithTags) -> list[tuple[str, TagState]]:
    return [(tag.name, tag.state) for tag in item.tags]


# --------------------------------------------------------------------------- #
# Language detection
# --------------------------------------------------------------------------- #
def test_detect_language_returns_code_for_english():
    assert detect_language("Hello there, how are you today?") == "en"


@pytest.mark.parametrize(
    "text",
    [
        "",  # empty text makes langdetect raise internally
        "hmm",
        "Dobrý den, jak se máte?",  # Czech is not supported by pysbd
    ],
)
def test_detect_language_returns_none_when_unsupported(text):
    assert detect_language(text) is None


@pytest.mark.parametrize(
    "text",
    [
        "Hello there, how are you today?",
        "你好，今天天气不错。",
        "こんにちは、今日はいい天気ですね。",
        "hmm",
        "",
    ],
)
def test_detect_language_never_returns_an_unsupported_code(text):
    """Whatever is returned must be safe to hand to ``pysbd.Segmenter``."""
    detected = detect_language(text)
    assert detected is None or detected in SUPPORTED_LANGUAGES


@pytest.mark.xfail(
    reason=(
        "langdetect reports the region-qualified code 'zh-cn' while "
        "SUPPORTED_LANGUAGES only lists 'zh', so Chinese always falls back to the "
        "regex segmenter even though pysbd supports it"
    ),
    strict=False,
)
def test_chinese_is_routed_to_pysbd():
    assert detect_language("你好，今天天气不错。") == "zh"


# --------------------------------------------------------------------------- #
# Small helpers
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Hello.", True),
        ("Hello", False),
        ("Hi!", True),
        ("Are you there?", True),
        ("你好。", True),
        ("你好！", True),
        ("Hello...", True),
        ("Mr.", False),  # abbreviations are not sentence ends
        ("e.g.", False),
        ("", False),
        ("   ", False),
    ],
)
def test_is_complete_sentence(text, expected):
    assert is_complete_sentence(text) is expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("a,b", True),
        ("a、b", True),
        ("a，b", True),
        ("a،b", True),
        ("a;b", True),
        ("ab", False),
        ("", False),
    ],
)
def test_contains_comma(text, expected):
    assert contains_comma(text) is expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("a.", True),
        ("a,", True),
        ("a", False),
        ("", False),
    ],
)
def test_has_punctuation(text, expected):
    assert has_punctuation(text) is expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("a.", True),
        ("a!", True),
        ("你好。", True),
        ("a,", False),
        ("a", False),
        ("", False),
    ],
)
def test_contains_end_punctuation(text, expected):
    assert contains_end_punctuation(text) is expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Hello, world", ("Hello,", "world")),
        ("你好，世界", ("你好，", "世界")),
        ("no comma here", ("no comma here", "")),
    ],
)
def test_comma_splitter(text, expected):
    assert comma_splitter(text) == expected


def test_comma_splitter_empty_input_is_safe():
    split, remaining = comma_splitter("")
    assert not split
    assert remaining == ""


@pytest.mark.xfail(
    reason="COMMAS is scanned in list order instead of by position, so an earlier ';' is skipped",
    strict=False,
)
def test_comma_splitter_splits_at_the_earliest_comma():
    assert comma_splitter("a; b, c") == ("a;", "b, c")


# --------------------------------------------------------------------------- #
# Segmentation helpers
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Hello. How are you?", (["Hello.", "How are you?"], "")),
        ("Hello. How are", (["Hello."], "How are")),
        ("你好。你好吗？", (["你好。", "你好吗？"], "")),
        ("One! Two? Three.", (["One!", "Two?", "Three."], "")),
        ("", ([], "")),
        ("No punctuation here", ([], "No punctuation here")),
    ],
)
def test_segment_text_by_regex(text, expected):
    assert segment_text_by_regex(text) == expected


def test_segment_text_by_regex_does_not_emit_abbreviation_fragments():
    sentences, remaining = segment_text_by_regex("Mr. Smith is here.")
    assert "Mr." not in sentences  # the abbreviation is not a sentence of its own
    assert sentences == ["Mr. Smith is here."]  # ... but its text is not dropped
    assert remaining == ""


def test_segment_text_by_regex_keeps_a_trailing_abbreviation_in_the_remainder():
    sentences, remaining = segment_text_by_regex("Hello. Mr. Smith is")
    assert sentences == ["Hello."]
    assert remaining == "Mr. Smith is"


def test_abbreviations_are_not_lost_while_streaming():
    divider = SentenceDivider(segment_method="regex")
    _, items = process_with(divider, ["Mr. Smith is here. And done."])
    assert texts(items) == ["Mr. Smith is here.", "And done."]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            "Hello there. How are you? I am fine",
            (["Hello there.", "How are you?"], "I am fine"),
        ),
        ("Hello. How are you?", (["Hello.", "How are you?"], "")),
        ("你好。今天天气不错。", (["你好。", "今天天气不错。"], "")),
        ("", ([], "")),
    ],
)
def test_segment_text_by_pysbd(text, expected):
    assert segment_text_by_pysbd(text) == expected


def test_segment_text_by_pysbd_falls_back_to_regex_for_unsupported_language(
    monkeypatch,
):
    monkeypatch.setattr(sd, "detect_language", lambda text: None)
    assert segment_text_by_pysbd("Hello. Tail") == segment_text_by_regex("Hello. Tail")


def test_segment_text_by_pysbd_falls_back_to_regex_on_error(monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("segmenter exploded")

    monkeypatch.setattr(sd.pysbd, "Segmenter", boom)
    assert segment_text_by_pysbd("Hello. Tail") == segment_text_by_regex("Hello. Tail")


# --------------------------------------------------------------------------- #
# Streaming pipeline
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "chunks",
    [
        ["Hello. How are you?"],
        ["Hel", "lo. Ho", "w are you?"],
        list("Hello. How are you?"),
        ["Hello. ", "How ", "are you?"],
    ],
)
def test_complete_sentences_are_emitted_regardless_of_chunking(chunks):
    divider, items = process(chunks)
    assert texts(items) == ["Hello.", "How are you?"]
    assert all(isinstance(item, SentenceWithTags) for item in items)
    assert divider.complete_response == "Hello.How are you?"


def test_unfinished_tail_is_flushed_when_the_stream_ends():
    _, items = process(["Hello. Unfinished tail"])
    assert texts(items) == ["Hello.", "Unfinished tail"]


def test_fragment_without_punctuation_is_flushed():
    _, items = process(["Just a fragment"])
    assert texts(items) == ["Just a fragment"]


def test_empty_chunks_are_ignored():
    _, items = process(["", "Hi.", ""])
    assert texts(items) == ["Hi."]


def test_first_sentence_splits_at_comma_for_a_faster_first_response():
    divider = SentenceDivider(faster_first_response=True)
    _, items = process_with(divider, ["Hello, how are you? I am fine."])
    assert texts(items) == ["Hello,", "how are you?", "I am fine."]


def test_first_sentence_is_not_split_when_faster_first_response_is_disabled():
    divider = SentenceDivider(faster_first_response=False)
    _, items = process_with(divider, ["Hello, how are you? I am fine."])
    assert texts(items) == ["Hello, how are you?", "I am fine."]


def test_only_the_first_sentence_is_split_at_a_comma():
    divider = SentenceDivider(faster_first_response=True)
    _, items = process_with(divider, ["a, b, c."])
    assert texts(items) == ["a,", "b, c."]


def test_dictionary_items_are_passed_through_untouched():
    payload = {"type": "tool_call", "id": 1}
    divider, items = process(["Hello. ", payload, " Next."])
    assert len(items) == 3
    assert items[1] is payload
    assert texts(items) == ["Hello.", "Next."]
    assert divider.complete_response == "Hello.Next."


def test_unexpected_item_types_are_ignored():
    _, items = process(["Hi. ", 42, "More."])
    assert texts(items) == ["Hi.", "More."]


def test_segment_method_regex_is_used_when_requested():
    divider = SentenceDivider(segment_method="regex")
    _, items = process_with(divider, ["Hello. How are you? Fine"])
    assert texts(items) == ["Hello.", "How are you?", "Fine"]


def test_reset_clears_buffered_state():
    divider, _ = process(["Hello, there"])
    divider.reset()
    assert divider._buffer == ""
    assert divider._is_first_sentence is True
    assert divider._tag_stack == []


def test_process_stream_starts_from_a_clean_state():
    divider = SentenceDivider()
    _, first = process_with(divider, ["One. Two."])
    _, second = process_with(divider, ["Three. Four."])
    assert texts(first) == ["One.", "Two."]
    assert texts(second) == ["Three.", "Four."]
    assert divider.complete_response == "Three.Four."


# --------------------------------------------------------------------------- #
# Tags
# --------------------------------------------------------------------------- #
def test_plain_text_carries_an_empty_none_tag():
    _, items = process(["Hello."])
    assert tag_states(items[0]) == [("", TagState.NONE)]


def test_tags_are_emitted_as_their_own_items_with_their_state():
    _, items = process(["Hello. <think>let me think</think> Answer."])
    assert all(isinstance(item, SentenceWithTags) for item in items)
    assert texts(items) == ["Hello.", "<think>", "let me think", "</think>", "Answer."]
    assert tag_states(items[1]) == [("think", TagState.START)]
    assert tag_states(items[2]) == [("think", TagState.INSIDE)]
    assert tag_states(items[3]) == [("think", TagState.END)]
    assert tag_states(items[4]) == [("", TagState.NONE)]


def test_text_before_a_tag_is_emitted_without_tags():
    _, items = process(["Some text <think>inner</think>after."], valid_tags=["think"])
    assert texts(items)[0] == "Some text"
    assert tag_states(items[0]) == [("", TagState.NONE)]
    assert texts(items)[1] == "<think>"


def test_nested_tags_are_reported_from_outermost_to_innermost():
    _, items = process(
        ["<outer>x<inner>y</inner>z</outer>Done."], valid_tags=["outer", "inner"]
    )
    assert texts(items) == [
        "<outer>",
        "x",
        "<inner>",
        "y",
        "</inner>",
        "z",
        "</outer>",
        "Done.",
    ]
    assert tag_states(items[1]) == [("outer", TagState.INSIDE)]
    assert tag_states(items[3]) == [
        ("outer", TagState.INSIDE),
        ("inner", TagState.INSIDE),
    ]
    assert tag_states(items[7]) == [("", TagState.NONE)]


def test_self_closing_tag_is_reported_as_self():
    _, items = process(["<think/>hello."], valid_tags=["think"])
    assert texts(items) == ["<think/>", "hello."]
    assert tag_states(items[0]) == [("think", TagState.SELF_CLOSING)]


def test_unmatched_closing_tag_does_not_break_the_stream():
    _, items = process(["</think>hi."], valid_tags=["think"])
    assert texts(items) == ["</think>", "hi."]
    assert tag_states(items[0]) == [("think", TagState.END)]
    assert tag_states(items[1]) == [("", TagState.NONE)]


def test_unknown_tags_are_left_in_the_text():
    _, items = process(["<unknown>kept</unknown> Done."], valid_tags=["think"])
    assert "<unknown>kept</unknown>" in " ".join(texts(items))
    assert tag_states(items[0]) == [("", TagState.NONE)]


def test_complete_response_concatenates_every_yielded_sentence():
    divider, items = process(["Hello. <think>hmm</think>Bye."])
    assert divider.complete_response == "".join(texts(items))
    assert divider.complete_response == "Hello.<think>hmm</think>Bye."
