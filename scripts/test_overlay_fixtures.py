"""Keep ``tests/fixtures/overlay-wire.json`` honest.

The fixture is a build artifact: ``scripts/export_overlay_fixtures.py`` runs the
real backend builders and dumps the frames, and ``scripts/test_overlay_wire.js``
replays them through ``web_tool/overlay-protocol.js``. This test is the link in
the middle — it fails when the backend changes and nobody regenerated the file,
so the JavaScript suite can never pass against a stale contract.

    python scripts/test_overlay_fixtures.py
    python scripts/export_overlay_fixtures.py        # to fix a failure

Importing the exporter installs the same shims as ``scripts/test_stage_obs.py``
(``loguru``/``numpy``/``pydantic``/``pydub``), which is harmless here because
every test file runs in its own process.
"""

import json
import os
import sys
import unittest

scripts_dir = os.path.abspath(os.path.dirname(__file__))
project_root = os.path.abspath(os.path.join(scripts_dir, ".."))
for path in (project_root, scripts_dir):
    if path not in sys.path:
        sys.path.insert(0, path)

import export_overlay_fixtures as exporter  # noqa: E402

TURN_SCENARIOS = (
    "turn_wav_two_chunks",
    "turn_mp3_two_chunks",
    "turn_silent_and_forwarded",
)
STAGE_SCENARIOS = (
    "stage_background_only",
    "stage_with_props",
    "stage_transition_none",
)


def _load() -> dict:
    with open(exporter.FIXTURE_PATH, encoding="utf-8") as handle:
        return json.load(handle)


class FixtureFileTests(unittest.TestCase):
    """The committed file must match the current backend code."""

    def test_fixture_is_committed(self):
        self.assertTrue(
            os.path.exists(exporter.FIXTURE_PATH),
            "missing tests/fixtures/overlay-wire.json; "
            "run: python scripts/export_overlay_fixtures.py",
        )

    def test_fixture_matches_the_generator(self):
        with open(exporter.FIXTURE_PATH, encoding="utf-8") as handle:
            current = handle.read().replace("\r\n", "\n")
        self.assertEqual(
            current,
            exporter.render(),
            "tests/fixtures/overlay-wire.json is stale; "
            "run: python scripts/export_overlay_fixtures.py",
        )

    def test_header_is_descriptive(self):
        fixture = _load()
        self.assertEqual(fixture["schema"], exporter.SCHEMA_VERSION)
        self.assertEqual(fixture["generated_by"], exporter.GENERATOR)
        self.assertIn("stage-update", fixture["contract"])
        self.assertNotIn(
            "stubs_used",
            fixture,
            "the fixture must not depend on the environment that generated it",
        )


class FixtureContentTests(unittest.TestCase):
    """The scenarios must cover the contract the overlay depends on."""

    def setUp(self):
        self.fixture = _load()
        self.scenarios = {s["name"]: s for s in self.fixture["scenarios"]}

    def test_scenario_names_are_unique(self):
        names = [s["name"] for s in self.fixture["scenarios"]]
        self.assertEqual(len(names), len(set(names)))

    def test_every_frame_is_json_with_a_type(self):
        for name, scenario in self.scenarios.items():
            frames = scenario["frames"] + scenario.get("after_ack", [])
            self.assertTrue(frames, f"{name} carries no frames")
            for frame in frames:
                self.assertIsInstance(frame, str, name)
                message = json.loads(frame)
                self.assertIsInstance(message.get("type"), str, name)

    def test_turn_scenarios_split_around_the_ack(self):
        for name in TURN_SCENARIOS:
            scenario = self.scenarios[name]
            types = [json.loads(f)["type"] for f in scenario["frames"]]
            self.assertEqual(types[-1], "backend-synth-complete", name)
            after = [json.loads(f) for f in scenario["after_ack"]]
            self.assertEqual(
                [m["type"] for m in after], ["force-new-message", "control"]
            )
            self.assertEqual(after[-1]["text"], "conversation-chain-end")

    def test_silent_turn_has_no_playable_audio(self):
        chunks = [
            json.loads(f)
            for f in self.scenarios["turn_silent_and_forwarded"]["frames"]
            if json.loads(f)["type"] == "audio"
        ]
        self.assertEqual(len(chunks), 2)
        for chunk in chunks:
            self.assertIsNone(chunk["audio"])
        self.assertTrue(any(chunk["forwarded"] for chunk in chunks))

    def test_interrupt_scenario_uses_the_backend_builder(self):
        frames = [
            json.loads(f) for f in self.scenarios["interrupt_after_chunk"]["frames"]
        ]
        self.assertEqual(
            frames[-1], exporter.conversation_utils.build_interrupt_signal()
        )
        self.assertNotIn("backend-synth-complete", [f["type"] for f in frames])

    def test_stage_scenarios_are_sanitised(self):
        for name in STAGE_SCENARIOS:
            message = json.loads(self.scenarios[name]["frames"][0])
            self.assertEqual(message["type"], "stage-update", name)

        props = json.loads(self.scenarios["stage_with_props"]["frames"][0])["props"]
        self.assertEqual([p["id"] for p in props], ["card_1", "card_2"])
        self.assertEqual(props[1]["x"], 1.0)
        self.assertEqual(props[1]["y"], 0.0)
        self.assertNotIn(
            "props", json.loads(self.scenarios["stage_background_only"]["frames"][0])
        )


if __name__ == "__main__":
    unittest.main()
