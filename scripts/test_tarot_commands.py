"""Unit tests for on-demand draws: chat commands and the shared presenter.

Pure standard library (``utils/tarot_commands.py``), so a bare interpreter is
enough. The HTTP/WebSocket glue is thin on purpose: it only calls
``build_draw_result`` and sends the result.

    python scripts/test_tarot_commands.py
    python scripts/test_tarot_commands.py -v ParseCommandTests
"""

import json
import os
import sys
import unittest

# Add project root to path to enable imports (same as the live scripts).
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.open_llm_vtuber.utils import tarot  # noqa: E402
from src.open_llm_vtuber.utils.tarot_commands import (  # noqa: E402
    CHAT_COMMANDS,
    DRAW_STAGE,
    MAX_QUESTION,
    build_draw_result,
    parse_draw_command,
)


class ParseCommandTests(unittest.TestCase):
    """What the chat writes must never reach the LLM by accident."""

    def test_plain_messages_are_not_commands(self):
        for text in (None, 123, [], "", "   ", "hola", "carta", "!cartas"):
            self.assertIsNone(parse_draw_command(text), text)

    def test_commands_default_to_one_card(self):
        for command in CHAT_COMMANDS:
            request = parse_draw_command(command)
            self.assertEqual(request.count, 1, command)
            self.assertEqual(request.question, "", command)

    def test_case_and_spaces_do_not_matter(self):
        request = parse_draw_command("   !Tirada   2   ")
        self.assertEqual(request.count, 2)
        self.assertEqual(request.question, "")

    def test_count_and_question(self):
        request = parse_draw_command("!tarot 3 ¿me cambio de trabajo?")
        self.assertEqual(request.count, 3)
        self.assertEqual(request.question, "¿me cambio de trabajo?")

    def test_question_without_count(self):
        request = parse_draw_command("!carta ¿voy a mudarme?")
        self.assertEqual(request.count, 1)
        self.assertEqual(request.question, "¿voy a mudarme?")

    def test_non_numeric_second_word_is_the_question(self):
        request = parse_draw_command("!carta para el público")
        self.assertEqual(request.count, 1)
        self.assertEqual(request.question, "para el público")

    def test_count_out_of_range_is_an_error(self):
        for command in ("!carta 0", "!tirada 9", "/carta 42"):
            with self.assertRaises(ValueError, msg=command):
                parse_draw_command(command)

    def test_question_is_truncated(self):
        request = parse_draw_command("!carta " + "x" * 500)
        self.assertEqual(len(request.question), MAX_QUESTION)


class BuildResultTests(unittest.TestCase):
    """Overlay payload and LLM brief are built from the same cards."""

    def test_payload_and_brief_agree(self):
        result = build_draw_result(count=3, question="¿y el amor?", seed=2026)

        self.assertEqual(len(result.cards), 3)
        self.assertEqual(result.payload["stage"], DRAW_STAGE)
        self.assertNotIn("background", result.payload)

        labels = [prop["label"] for prop in result.payload["props"]]
        self.assertEqual(labels, [card.card.name for card in result.cards])

        for card in result.cards:
            self.assertIn(card.card.name, result.brief)
        self.assertIn("¿y el amor?", result.brief)

    def test_seed_is_reproducible(self):
        first = build_draw_result(count=3, seed=77)
        second = build_draw_result(count=3, seed=77)
        self.assertEqual(
            [card.card.id for card in first.cards],
            [card.card.id for card in second.cards],
        )

    def test_question_is_cleaned_and_capped(self):
        result = build_draw_result(question="  " + "y" * 400 + "  ")
        self.assertEqual(result.question, "y" * MAX_QUESTION)

    def test_count_is_validated(self):
        for count in (0, tarot.MAX_CARDS + 1):
            with self.assertRaises(ValueError):
                build_draw_result(count=count)

    def test_summary_is_json_friendly(self):
        result = build_draw_result(count=2, question="¿sí o no?", seed=5)
        summary = json.loads(json.dumps(result.summary()))

        self.assertEqual(summary["question"], "¿sí o no?")
        self.assertEqual(summary["stage"], DRAW_STAGE)
        self.assertEqual(len(summary["cards"]), 2)
        for card, drawn in zip(summary["cards"], result.cards):
            self.assertEqual(card["id"], drawn.card.id)
            self.assertEqual(card["name"], drawn.card.name)
            self.assertEqual(card["reversed"], drawn.reversed)
            self.assertEqual(card["position"], drawn.position)
            self.assertEqual(card["keywords"], list(drawn.card.keywords))

    def test_delivery_flags_start_empty(self):
        result = build_draw_result(count=1, seed=1)
        self.assertEqual(result.delivered, 0)
        self.assertFalse(result.spoken)


if __name__ == "__main__":
    unittest.main()
