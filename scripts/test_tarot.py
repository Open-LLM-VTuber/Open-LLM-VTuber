"""Unit tests for the tarot deck, spreads and the text-card props.

Standalone and dependency-free on purpose (same approach as
``scripts/test_stage_obs.py``): ``utils/tarot.py`` and ``utils/stage.py`` are
stdlib-only, so a bare interpreter is enough.

    python scripts/test_tarot.py
    python scripts/test_tarot.py -v DrawnCardTests
"""

import os
import sys
import unittest

# Add project root to path to enable imports (same as the live scripts).
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.open_llm_vtuber.utils import tarot  # noqa: E402
from src.open_llm_vtuber.utils.stage import build_stage_payload  # noqa: E402


class DeckTests(unittest.TestCase):
    """The deck is data: wrong data shows on stream."""

    def test_twenty_two_major_arcana(self):
        self.assertEqual(len(tarot.DECK), 22)
        self.assertEqual(
            tarot.deck_ids(), [f"major_{index:02d}" for index in range(22)]
        )

    def test_ids_and_names_are_unique(self):
        ids = [card.id for card in tarot.DECK]
        names = [card.name for card in tarot.DECK]
        self.assertEqual(len(set(ids)), len(ids))
        self.assertEqual(len(set(names)), len(names))

    def test_every_card_is_readable(self):
        for card in tarot.DECK:
            self.assertTrue(card.name.strip(), card.id)
            self.assertGreaterEqual(len(card.keywords), 2, card.id)
            self.assertTrue(all(word.strip() for word in card.keywords), card.id)
            self.assertTrue(card.upright.strip(), card.id)
            self.assertTrue(card.reversed.strip(), card.id)

    def test_lookup_by_id(self):
        self.assertEqual(tarot.card_by_id("major_16").name, "La Torre")
        self.assertIsNone(tarot.card_by_id("major_99"))
        self.assertIsNone(tarot.card_by_id(""))


class DrawTests(unittest.TestCase):
    """``draw_cards`` is the only random part, so it must be reproducible."""

    def test_same_seed_same_spread(self):
        first = tarot.draw_cards(3, seed=2026)
        second = tarot.draw_cards(3, seed=2026)
        self.assertEqual(
            [(card.card.id, card.reversed) for card in first],
            [(card.card.id, card.reversed) for card in second],
        )

    def test_different_seeds_differ(self):
        first = [card.card.id for card in tarot.draw_cards(3, seed=1)]
        second = [card.card.id for card in tarot.draw_cards(3, seed=2)]
        self.assertNotEqual(first, second)

    def test_a_spread_has_no_repeated_cards(self):
        for seed in range(20):
            drawn = tarot.draw_cards(3, seed=seed)
            self.assertEqual(len({card.card.id for card in drawn}), 3, seed)

    def test_positions_match_the_spread_size(self):
        self.assertEqual(
            [card.position for card in tarot.draw_cards(1, seed=5)],
            ["Carta del día"],
        )
        self.assertEqual(
            [card.position for card in tarot.draw_cards(3, seed=5)],
            ["Pasado", "Presente", "Futuro"],
        )

    def test_reversed_can_be_disabled(self):
        for seed in range(10):
            drawn = tarot.draw_cards(3, seed=seed, allow_reversed=False)
            self.assertFalse(any(card.reversed for card in drawn), seed)

    def test_count_is_validated(self):
        for count in (0, 4, -1):
            with self.assertRaises(ValueError):
                tarot.draw_cards(count)
        for count in ("2", 1.0, True, None):
            with self.assertRaises(ValueError):
                tarot.draw_cards(count)


class DrawnCardTests(unittest.TestCase):
    """Label/sublabel are what the overlay draws and the LLM reads."""

    def setUp(self):
        self.tower = tarot.card_by_id("major_16")
        self.upright = tarot.DrawnCard(self.tower, reversed=False, position="Presente")
        self.reversed = tarot.DrawnCard(self.tower, reversed=True, position="Futuro")

    def test_label_is_the_card_name(self):
        self.assertEqual(self.upright.label(), "La Torre")

    def test_sublabel_has_the_keywords(self):
        self.assertEqual(self.upright.sublabel(), "ruptura · verdad · derrumbe")

    def test_reversed_sublabel_says_so(self):
        self.assertIn("invertida", self.reversed.sublabel())

    def test_meaning_follows_the_orientation(self):
        self.assertEqual(self.upright.meaning(), self.tower.upright)
        self.assertEqual(self.reversed.meaning(), self.tower.reversed)

    def test_describe(self):
        self.assertEqual(self.upright.describe(), "Presente: La Torre")
        self.assertEqual(self.reversed.describe(), "Futuro: La Torre (invertida)")
        self.assertEqual(tarot.DrawnCard(self.tower).describe(), "La Torre")


class DrawPropTests(unittest.TestCase):
    """The props reach the overlay through the normal stage sanitiser."""

    def test_props_are_spread_and_point_to_the_art(self):
        drawn = tarot.draw_cards(3, seed=2026)
        props = tarot.build_draw_props(drawn)

        self.assertEqual([prop["id"] for prop in props], ["card_1", "card_2", "card_3"])
        self.assertEqual([prop["x"] for prop in props], [0.28, 0.5, 0.72])
        self.assertTrue(all(prop["y"] == 0.68 for prop in props))
        for prop, card in zip(props, drawn):
            self.assertEqual(prop["src"], f"/bg/cards/{card.card.id}.jpg")
            self.assertEqual(prop["scale"], 0.55)
            self.assertEqual(prop["rot"], 180 if card.reversed else 0)
            self.assertNotIn("label", prop, "art props are images, not text cards")

    def test_scale_shrinks_with_the_spread(self):
        self.assertEqual(
            tarot.build_draw_props(tarot.draw_cards(1, seed=1))[0]["scale"], 0.85
        )
        self.assertEqual(
            tarot.build_draw_props(tarot.draw_cards(2, seed=1))[0]["scale"], 0.7
        )

    def test_text_props_are_the_fallback(self):
        drawn = tarot.draw_cards(2, seed=9)
        props = tarot.build_draw_props(drawn, art_prefix=None)

        for prop, card in zip(props, drawn):
            self.assertEqual(prop["label"], card.label())
            self.assertEqual(prop["sublabel"], card.sublabel())
            self.assertNotIn("src", prop)
            self.assertNotIn("scale", prop, "text cards are sized by the overlay CSS")

    def test_single_card_is_centred(self):
        props = tarot.build_draw_props(tarot.draw_cards(1, seed=3))
        self.assertEqual(len(props), 1)
        self.assertEqual(props[0]["x"], 0.5)

    def test_no_cards_no_props(self):
        self.assertEqual(tarot.build_draw_props([]), [])

    def test_payload_needs_no_background(self):
        props = tarot.build_draw_props(tarot.draw_cards(2, seed=9), art_prefix=None)
        payload = build_stage_payload(stage="card_of_the_day", props=props)

        self.assertEqual(payload["type"], "stage-update")
        self.assertNotIn("background", payload)
        self.assertEqual(len(payload["props"]), 2)
        for prop in payload["props"]:
            self.assertIn("label", prop)
            self.assertIn("sublabel", prop)

    def test_art_payload_needs_no_background(self):
        props = tarot.build_draw_props(tarot.draw_cards(1, seed=9))
        payload = build_stage_payload(stage="tarot_draw", props=props)

        self.assertNotIn("background", payload)
        self.assertRegex(payload["props"][0]["src"], r"^/bg/cards/major_\d\d\.jpg$")


class CardArtTests(unittest.TestCase):
    """The default props point at files that must exist on disk."""

    def test_every_card_has_art(self):
        folder = os.path.join(project_root, "backgrounds", "cards")
        for card in tarot.DECK:
            path = os.path.join(folder, f"{card.id}.{tarot.CARD_ART_EXT}")
            self.assertTrue(os.path.exists(path), path)
            self.assertGreater(os.path.getsize(path), 10_000, f"{path} looks empty")

    def test_placeholder_deck_is_available_too(self):
        # The SVG generator is the fallback for a repo without the JPEG deck.
        folder = os.path.join(project_root, "backgrounds", "cards")
        for card in tarot.DECK:
            path = os.path.join(folder, f"{card.id}.svg")
            self.assertTrue(os.path.exists(path), path)

    def test_art_is_served_where_the_props_point(self):
        self.assertEqual(tarot.CARD_ART_DIR, "/bg/cards")
        self.assertEqual(tarot.CARD_ART_EXT, "jpg")

    def test_props_survive_the_sanitiser(self):
        props = tarot.build_draw_props(tarot.draw_cards(3, seed=1))
        payload = build_stage_payload(props=props)
        self.assertEqual(
            [prop["id"] for prop in payload["props"]],
            ["card_1", "card_2", "card_3"],
        )


class TarotBriefTests(unittest.TestCase):
    """The brief is the only thing that tells the LLM what is on screen."""

    def setUp(self):
        self.drawn = tarot.draw_cards(3, seed=7)
        self.brief = tarot.build_tarot_brief(self.drawn, "¿Voy a cambiar de trabajo?")

    def test_it_lists_every_card(self):
        for card in self.drawn:
            self.assertIn(card.card.name, self.brief)
            self.assertIn(card.position, self.brief)
            self.assertIn(card.meaning(), self.brief)

    def test_it_includes_the_question(self):
        self.assertIn("¿Voy a cambiar de trabajo?", self.brief)

    def test_it_forbids_inventing_cards(self):
        self.assertIn("No inventes otras cartas", self.brief)

    def test_question_is_optional(self):
        self.assertNotIn("Pregunta:", tarot.build_tarot_brief(self.drawn))

    def test_asker_is_named(self):
        brief = tarot.build_tarot_brief(self.drawn, "¿y el amor?", asker="pepe")
        self.assertIn("Pregunta de pepe: ¿y el amor?", brief)
        self.assertIn("Responde directamente a pepe.", brief)

    def test_asker_without_question(self):
        brief = tarot.build_tarot_brief(self.drawn, asker="ana")
        self.assertIn("Pregunta de ana", brief)
        self.assertIn("todavía no ha escrito su pregunta", brief)

    def test_no_cards_no_brief(self):
        self.assertEqual(tarot.build_tarot_brief([]), "")


if __name__ == "__main__":
    unittest.main()
