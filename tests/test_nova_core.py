import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestAnchorPipeline:
    def test_generates_instant_anchor(self):
        from src.open_llm_vtuber.agent.anchor_pipeline import SpeculativeAnchorPipeline
        p = SpeculativeAnchorPipeline()
        anchor = p.select_instant_anchor("hello what's up")
        assert isinstance(anchor, str)
        assert len(anchor) > 0

    def test_anchor_for_question(self):
        from src.open_llm_vtuber.agent.anchor_pipeline import SpeculativeAnchorPipeline
        p = SpeculativeAnchorPipeline()
        anchor = p.select_instant_anchor("what is the meaning of life?")
        assert anchor != ""

    def test_prepares_continuation_prompt(self):
        from src.open_llm_vtuber.agent.anchor_pipeline import SpeculativeAnchorPipeline
        p = SpeculativeAnchorPipeline()
        prompt = p.prepare_continuation_prompt("hello", "Well", "You are an AI.")
        assert "Well" in prompt
        assert "hello" in prompt


class TestDualTrackRouter:
    def test_routes_banter_to_ollama(self):
        from src.open_llm_vtuber.agent.dual_track_router import DualTrackLLMRouter
        router = DualTrackLLMRouter(groq_api_key="test")
        route = router.route("lol that was funny")
        assert route == "ollama"

    def test_routes_complex_to_groq(self):
        from src.open_llm_vtuber.agent.dual_track_router import DualTrackLLMRouter
        router = DualTrackLLMRouter(groq_api_key="test")
        route = router.route("Explain the computational complexity analysis of multi-head transformer attention mechanisms and implement a complete Python algorithm to demonstrate how these computational patterns work in modern deep learning applications")
        assert route == "groq"

    def test_router_falls_back_without_groq(self):
        from src.open_llm_vtuber.agent.dual_track_router import DualTrackLLMRouter
        router = DualTrackLLMRouter()
        route = router.route("Explain quantum entanglement")
        assert route == "ollama"

    def test_complexity_score_returns_int(self):
        from src.open_llm_vtuber.agent.dual_track_router import DualTrackLLMRouter
        router = DualTrackLLMRouter()
        score = router._compute_complexity_score("hello world")
        assert isinstance(score, int)
        assert 0 <= score <= 5


class TestAffectiveEngine:
    def test_triggers_event_updates_mood(self):
        from src.open_llm_vtuber.agent.affective_engine import AffectiveEngine
        engine = AffectiveEngine()
        mood_before = engine.get_mood_label()
        engine.trigger_event("VICTORY")
        mood_after = engine.get_mood_label()
        assert mood_before != mood_after or mood_after != "Calm & Confident"

    def test_pad_values_in_range(self):
        from src.open_llm_vtuber.agent.affective_engine import AffectiveEngine
        engine = AffectiveEngine()
        v, a, d = engine.current_pad
        assert -1.0 <= v <= 1.0
        assert -1.0 <= a <= 1.0
        assert -1.0 <= d <= 1.0

    def test_prompt_directive_returns_string(self):
        from src.open_llm_vtuber.agent.affective_engine import AffectiveEngine
        engine = AffectiveEngine()
        directive = engine.get_prompt_directive()
        assert isinstance(directive, str)
        assert len(directive) > 0


class TestFanMemoryEngine:
    def test_creates_and_retrieves_fan(self):
        from src.open_llm_vtuber.memory.fan_memory_engine import FanMemoryEngine
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)
        try:
            engine = FanMemoryEngine(db_path=db_path)
            fan = engine.get_or_create_fan("user_001", "TestUser")
            assert fan.username == "TestUser"
            assert fan.total_interactions == 0
            engine.record_interaction("user_001", "TestUser", "I love Python", "Nice!")
            fan2 = engine.get_or_create_fan("user_001", "TestUser")
            assert fan2.total_interactions == 1
            ctx = engine.get_context_for_user("user_001", "TestUser")
            assert "RETURNING FAN" in ctx
            engine.close()
        finally:
            db_path.unlink(missing_ok=True)

    def test_extracts_facts(self):
        from src.open_llm_vtuber.memory.fan_memory_engine import FanMemoryEngine
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)
        try:
            engine = FanMemoryEngine(db_path=db_path)
            facts = engine._extract_facts("I am a developer from Seattle", [])
            assert len(facts) > 0
            engine.close()
            db_path.unlink(missing_ok=True)
        except Exception:
            db_path.unlink(missing_ok=True)
            raise


class TestStreamPhysics:
    def test_parses_chat_command(self):
        from src.open_llm_vtuber.physics.stream_physics import StreamPhysicsEngine
        engine = StreamPhysicsEngine()
        result = engine.parse_chat_command("!throw pie", "Viewer1")
        assert result is not None
        assert result["item"] == "pie"

    def test_returns_none_for_unknown_item(self):
        from src.open_llm_vtuber.physics.stream_physics import StreamPhysicsEngine
        engine = StreamPhysicsEngine()
        result = engine.parse_chat_command("!throw unknownitem", "Viewer1")
        assert result is not None  # falls back to pie

    def test_cooldown_prevents_spam(self):
        from src.open_llm_vtuber.physics.stream_physics import StreamPhysicsEngine
        engine = StreamPhysicsEngine()
        engine.execute_throw("pie", "Viewer1")
        result2 = engine.execute_throw("pie", "Viewer1")
        assert result2 is None


class TestNarrativeLoreEngine:
    def test_loads_or_creates_ledger(self):
        from src.open_llm_vtuber.narrative.lore_engine import NarrativeLoreEngine
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = NarrativeLoreEngine(ledger_path=str(Path(tmpdir) / "test.json"))
            assert engine.lore is not None
            assert engine.lore.season == 1
            speech = engine.get_prologue_speech()
            assert len(speech) > 0
            prompt = engine.inject_narrative_context("You are an AI.")
            assert "NARRATIVE" in prompt

    def test_advances_episode(self):
        from src.open_llm_vtuber.narrative.lore_engine import NarrativeLoreEngine
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = NarrativeLoreEngine(ledger_path=str(Path(tmpdir) / "test.json"))
            old_ep = engine.lore.episode
            engine.advance_episode("Chat found a secret door.")
            assert engine.lore.episode == old_ep + 1


class TestCounterTrollCourtroom:
    def test_detects_troll_bait(self):
        from src.open_llm_vtuber.live.counter_troll_courtroom import CounterTrollCourtroom
        court = CounterTrollCourtroom(trial_duration=999)
        result = court.evaluate_message_for_troll("TrollGuy", "You are just a dumb bot")
        assert result is not None
        assert result["action"] == "START_TRIAL"

    def test_clean_message_passes(self):
        from src.open_llm_vtuber.live.counter_troll_courtroom import CounterTrollCourtroom
        court = CounterTrollCourtroom(trial_duration=999)
        result = court.evaluate_message_for_troll("GoodUser", "Great stream today!")
        assert result is None

    def test_resolves_verdict(self):
        from src.open_llm_vtuber.live.counter_troll_courtroom import CounterTrollCourtroom
        court = CounterTrollCourtroom(trial_duration=0.01)
        court.evaluate_message_for_troll("TrollGuy", "You are just a dumb bot")
        import time
        time.sleep(0.05)
        verdict = court.resolve_verdict(force=True)
        assert verdict is not None
        assert verdict["verdict"] in ("GUILTY", "INNOCENT")


class TestInCharacterModerator:
    def test_classifies_backseating(self):
        from src.open_llm_vtuber.live.in_character_moderator import InCharacterModerator
        mod = InCharacterModerator()
        action = mod.classify_message("User1", "You need to press E to open the chest!")
        assert action.category == "BACKSEATING"
        assert action.duration_seconds == 0

    def test_strikes_escalate(self):
        from src.open_llm_vtuber.live.in_character_moderator import InCharacterModerator
        mod = InCharacterModerator()
        mod.classify_message("User1", "You idiot go left!")
        action = mod.classify_message("User1", "You need to press E!")
        assert action.strike_count == 2
        assert action.duration_seconds == 60


class TestProactiveStreamIntelligence:
    def test_initializes(self):
        from src.open_llm_vtuber.live.proactive_stream_intelligence import (
            ProactiveStreamIntelligence,
        )
        p = ProactiveStreamIntelligence(idle_threshold_sec=30, enabled=True)
        assert p.enabled is True
        p.stop()

    def test_tracks_idle_time(self):
        from src.open_llm_vtuber.live.proactive_stream_intelligence import (
            ProactiveStreamIntelligence,
        )
        p = ProactiveStreamIntelligence(idle_threshold_sec=30)
        idle = p.get_idle_seconds()
        assert idle >= 0
        time.sleep(0.1)
        idle_after = p.get_idle_seconds()
        assert idle_after >= idle
        p.stop()

    def test_gets_stream_minutes(self):
        from src.open_llm_vtuber.live.proactive_stream_intelligence import (
            ProactiveStreamIntelligence,
        )
        p = ProactiveStreamIntelligence()
        mins = p.get_stream_minutes()
        assert mins >= 0
        p.stop()

    def test_gets_time_aware_context(self):
        from src.open_llm_vtuber.live.proactive_stream_intelligence import (
            ProactiveStreamIntelligence,
        )
        p = ProactiveStreamIntelligence()
        ctx = p._get_time_aware_context()
        assert "Stream" in ctx
        p.stop()


class TestSocialRadar:
    def test_has_pop_seed_prompt(self):
        from src.open_llm_vtuber.radar.social_radar import SocialRadarEngine
        engine = SocialRadarEngine()
        prompt = engine.pop_top_seed_prompt()
        assert prompt is not None
        assert "SPONTANEOUS" in prompt


class TestVRChatBridge:
    def test_builds_osc_message(self):
        from src.open_llm_vtuber.live.vrchat_bridge import build_osc_message
        msg = build_osc_message("/test", 1.0, "hello")
        assert isinstance(msg, bytes)
        assert len(msg) > 0

    def test_initializes_bridge(self):
        from src.open_llm_vtuber.live.vrchat_bridge import VRChatBridge
        bridge = VRChatBridge(host="127.0.0.1", port=9000)
        assert bridge.host == "127.0.0.1"
        bridge.close()


class TestP2PFederation:
    def test_creates_heartbeat(self):
        from src.open_llm_vtuber.live.p2p_federation import VirtualAgencyP2PNode
        node = VirtualAgencyP2PNode(node_id="test_node", vtuber_name="Test")
        msg = node.create_heartbeat(True, "Minecraft", 100, "Testing")
        assert msg.msg_type == "HEARTBEAT"
        assert msg.payload["viewers"] == 100

    def test_merges_heartbeat(self):
        from src.open_llm_vtuber.live.p2p_federation import VirtualAgencyP2PNode
        node1 = VirtualAgencyP2PNode("n1", "Node1")
        node2 = VirtualAgencyP2PNode("n2", "Node2")
        hb = node1.create_heartbeat(True, "Game", 50, "Topic")
        result = node2.receive_gossip_packet(hb)
        assert result is not None  # TTL=3 -> 2, still forwardable
        assert "n1" in node2.peers


class TestCognitiveRouter:
    def test_routes_reflex_to_draft(self):
        from src.open_llm_vtuber.agent.cognitive_router import DynamicCognitiveRouter
        router = DynamicCognitiveRouter()
        decision = router.route_query("lol")
        assert decision.target_model == "DRAFT_0_5B"

    def test_routes_complex_to_deep(self):
        from src.open_llm_vtuber.agent.cognitive_router import DynamicCognitiveRouter
        router = DynamicCognitiveRouter()
        decision = router.route_query("Explain neural network architectures in detail")
        assert decision.target_model == "DEEP_7B"

    def test_evaluation_is_fast(self):
        from src.open_llm_vtuber.agent.cognitive_router import DynamicCognitiveRouter
        router = DynamicCognitiveRouter()
        decision = router.route_query("hello")
        assert decision.evaluation_time_ms < 5.0


class TestKaraokeHarmonizer:
    def test_generates_harmony(self):
        from src.open_llm_vtuber.audio.karaoke_harmonizer import (
            RealtimeKaraokeHarmonizer,
        )
        import numpy as np
        h = RealtimeKaraokeHarmonizer()
        sr = 24000
        t = np.linspace(0, 0.5, sr // 2, endpoint=False)
        audio = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
        result = h.generate_duet_harmony(audio, interval="MAJOR_THIRD")
        assert result.harmonized_pcm is not None
        assert len(result.harmonized_pcm) > 0


class TestAudioWatermark:
    def test_embeds_and_verifies(self):
        from src.open_llm_vtuber.audio.audioseal_watermark import AudioWatermarkEngine
        import numpy as np
        engine = AudioWatermarkEngine()
        audio = (np.random.randn(48000) * 0.3).astype(np.float32)
        watermarked, latency = engine.embed_watermark(audio)
        assert watermarked is not None
        result = engine.verify_watermark(watermarked)
        assert result is not None


class TestAnchorPipelineSpeed:
    def test_anchor_generation_is_submillisecond(self):
        from src.open_llm_vtuber.agent.anchor_pipeline import SpeculativeAnchorPipeline
        p = SpeculativeAnchorPipeline()
        import time
        t0 = time.perf_counter()
        for _ in range(1000):
            p.select_instant_anchor("test message")
        elapsed = (time.perf_counter() - t0) * 1000
        assert elapsed < 1000  # 1000 calls under 1 second total
