"""Unit tests for the donation follow-up: pending donors and their frames.

Standard library only (``utils/donations.py``), so a bare interpreter is enough:

    python scripts/test_donations.py
"""

import os
import sys
import unittest

# Add project root to path to enable imports (same as the live scripts).
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.open_llm_vtuber.utils.donations import (  # noqa: E402
    MAX_GIFT_NAME,
    MAX_USERNAME,
    PendingDonors,
    build_donor_draw_payload,
    build_gift_thanks,
    normalize_username,
)


class Clock:
    """Controllable clock so the TTL never depends on real time."""

    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


class NormalizeTests(unittest.TestCase):
    def test_names_are_normalised(self):
        self.assertEqual(normalize_username("  @Pepe  "), "pepe")
        self.assertEqual(normalize_username("ANA"), "ana")
        self.assertEqual(normalize_username("x" * 200), "x" * MAX_USERNAME)

    def test_bad_values_become_empty(self):
        for value in (None, 12, [], "", "   "):
            self.assertEqual(normalize_username(value), "", value)


class PendingDonorTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.donors = PendingDonors(ttl_seconds=60, clock=self.clock)

    def test_a_donation_arms_one_question(self):
        self.assertEqual(self.donors.remember("@Pepe", gift="Rosa", coins=5), "pepe")
        self.assertEqual(len(self.donors), 1)

        entry = self.donors.consume("pepe")
        self.assertEqual(entry["gift"], "Rosa")
        self.assertEqual(entry["coins"], 5)

        # One-shot: the same gift cannot buy a second reading.
        self.assertIsNone(self.donors.consume("pepe"))
        self.assertEqual(len(self.donors), 0)

    def test_unknown_comment_consumes_nothing(self):
        self.donors.remember("pepe", gift="Rosa")
        self.assertIsNone(self.donors.consume("ana"))
        self.assertEqual(len(self.donors), 1)

    def test_entry_expires(self):
        self.donors.remember("pepe", gift="Rosa")
        self.clock.advance(61)
        self.assertIsNone(self.donors.consume("pepe"))
        self.assertEqual(len(self.donors), 0)

    def test_entry_is_fresh_before_the_ttl(self):
        self.donors.remember("pepe")
        self.clock.advance(59)
        self.assertIsNotNone(self.donors.consume("pepe"))

    def test_donors_are_independent(self):
        self.donors.remember("pepe", gift="Rosa")
        self.donors.remember("ana", gift="Leon", coins=20)
        self.assertEqual(self.donors.consume("ana")["gift"], "Leon")
        self.assertEqual(self.donors.consume("pepe")["gift"], "Rosa")

    def test_invalid_username_is_ignored(self):
        self.assertIsNone(self.donors.remember(None))
        self.assertIsNone(self.donors.remember("  "))
        self.assertEqual(len(self.donors), 0)

    def test_clear_forgets_everything(self):
        self.donors.remember("pepe")
        self.donors.clear()
        self.assertEqual(len(self.donors), 0)


class GiftThanksTests(unittest.TestCase):
    """The gift turn thanks, asks, and explicitly does not read yet."""

    def setUp(self):
        self.text = build_gift_thanks("@Pepe", "Rosa", count=3, coins=30)

    def test_it_names_the_donor_and_the_gift(self):
        self.assertIn("Pepe", self.text)
        self.assertIn("Rosa", self.text)
        self.assertIn("x3", self.text)
        self.assertIn("30 monedas", self.text)

    def test_it_asks_what_the_donor_needs(self):
        self.assertIn("qué quiere saber", self.text)
        self.assertIn("comentario", self.text)

    def test_it_forbids_reading_before_the_question(self):
        self.assertIn("No leas cartas todavía", self.text)

    def test_defaults_are_safe(self):
        text = build_gift_thanks(None)
        self.assertIn("alguien", text)
        self.assertIn("un regalo", text)
        self.assertNotIn("monedas", text)


class DonorPayloadTests(unittest.TestCase):
    def test_payload_is_a_tarot_draw_for_that_donor(self):
        payload = build_donor_draw_payload("@Pepe", "  ¿me quiere?  ", count=1)
        self.assertEqual(payload["type"], "tarot-draw")
        self.assertEqual(payload["asker"], "Pepe")
        self.assertEqual(payload["question"], "¿me quiere?")
        self.assertEqual(payload["count"], 1)

    def test_gift_name_is_capped(self):
        text = build_gift_thanks("pepe", "x" * 200)
        self.assertNotIn("x" * (MAX_GIFT_NAME + 1), text)


if __name__ == "__main__":
    unittest.main()
