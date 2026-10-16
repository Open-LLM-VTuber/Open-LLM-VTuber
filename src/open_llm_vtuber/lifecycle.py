"""
Nova Engine Lifecycle Manager.

Central orchestrator that initializes, starts, stops, and coordinates all
Nova AI Influencer modules. This is the single integration point between
the core Open-LLM-VTuber server and all Nova upgrade modules.

Each module is lazily initialized on first access to avoid breaking
existing functionality when a module is not needed.
"""

import asyncio
import threading
import time
from typing import Dict, Optional, Set
from loguru import logger


class NovaEngine:
    """
    Master lifecycle manager for all Nova AI Influencer modules.

    Usage:
        nova = NovaEngine()
        await nova.start()
        # ... server runs ...
        await nova.stop()
    """

    def __init__(self):
        self._initialized: Set[str] = set()
        self._running = False
        self._start_time: Optional[float] = None
        self._tasks: Dict[str, asyncio.Task] = {}
        self._init_locks: Dict[str, threading.Lock] = {}
        self._locks_guard = threading.Lock()

        # Core modules — eagerly initialized
        self._init_eager_modules()

    def _init_eager_modules(self):
        """Modules that initialize immediately on NovaEngine creation."""
        try:
            from .audio import DynamicBGMDucker
            self.bgm_ducker = DynamicBGMDucker()
            logger.info("[Nova] BGM Ducking ready")
        except Exception as e:
            logger.warning(f"[Nova] BGM Ducking unavailable: {e}")

        try:
            from .audio.vocal_fatigue_engine import VocalFatigueEngine
            self.vocal_fatigue = VocalFatigueEngine()
            logger.info("[Nova] Vocal Fatigue Engine ready")
        except Exception as e:
            logger.warning(f"[Nova] Vocal Fatigue unavailable: {e}")

        try:
            from .audio.sfx_conductor import DynamicSFXConductor
            self.sfx_conductor = DynamicSFXConductor()
            logger.info("[Nova] SFX Conductor ready")
        except Exception as e:
            logger.warning(f"[Nova] SFX Conductor unavailable: {e}")

        try:
            from .audio.audioseal_watermark import AudioWatermarkEngine
            self.audio_watermark = AudioWatermarkEngine()
            logger.info("[Nova] Audio Watermark ready")
        except Exception as e:
            logger.warning(f"[Nova] Audio Watermark unavailable: {e}")

        try:
            from .audio.earbud_copilot_bridge import EarbudCoPilotBridge
            self.earbud_bridge = EarbudCoPilotBridge()
            logger.info("[Nova] Earbud Co-Pilot ready")
        except Exception as e:
            logger.warning(f"[Nova] Earbud Co-Pilot unavailable: {e}")

    def _lazy_init(self, module_name: str):
        """Initialize a module on first access. Thread-safe via per-module lock."""
        if module_name in self._initialized:
            return

        with self._locks_guard:
            if module_name not in self._init_locks:
                self._init_locks[module_name] = threading.Lock()
            lock = self._init_locks[module_name]

        with lock:
            if module_name in self._initialized:
                return

        try:
            if module_name == "affective_engine":
                from .agent.affective_engine import AffectiveEngine
                self.affective_engine = AffectiveEngine()
                logger.info("[Nova] Affective Engine ready")

            elif module_name == "anchor_pipeline":
                from .agent.anchor_pipeline import SpeculativeAnchorPipeline
                self.anchor_pipeline = SpeculativeAnchorPipeline()
                logger.info("[Nova] Anchor Pipeline ready")

            elif module_name == "cognitive_router":
                from .agent.cognitive_router import DynamicCognitiveRouter
                self.cognitive_router = DynamicCognitiveRouter()
                logger.info("[Nova] Cognitive Router ready")

            elif module_name == "collab_squad":
                from .agent.collab_squad import ConversationalFloorArbiter
                agents = []
                self.collab_squad = ConversationalFloorArbiter(agents)
                logger.info("[Nova] Collab Squad ready")

            elif module_name == "dual_track_router":
                from .agent.dual_track_router import DualTrackLLMRouter
                self.dual_track_router = DualTrackLLMRouter()
                logger.info("[Nova] Dual-Track Router ready")

            elif module_name == "rap_battle":
                from .agent.rap_battle_engine import FreestyleRapBattleEngine
                self.rap_battle = FreestyleRapBattleEngine()
                logger.info("[Nova] Rap Battle Engine ready")

            elif module_name == "fan_memory":
                from .memory.fan_memory_engine import FanMemoryEngine
                self.fan_memory = FanMemoryEngine()
                logger.info("[Nova] Fan Memory Engine ready")

            elif module_name == "parasocial_crm":
                from .memory.parasocial_crm import ParasocialCRM
                self.parasocial_crm = ParasocialCRM()
                logger.info("[Nova] Parasocial CRM ready")

            elif module_name == "narrative":
                from .narrative import NarrativeLoreEngine
                self.narrative_engine = NarrativeLoreEngine()
                logger.info("[Nova] Narrative Engine ready")

            elif module_name == "physics":
                from .physics import StreamPhysicsEngine
                self.stream_physics = StreamPhysicsEngine()
                logger.info("[Nova] Stream Physics ready")

            elif module_name == "radar":
                from .radar import SocialRadarEngine
                self.social_radar = SocialRadarEngine()
                logger.info("[Nova] Social Radar ready")

            elif module_name == "proactive":
                from .live.proactive_stream_intelligence import (
                    ProactiveStreamIntelligence,
                )
                self.proactive_intelligence = ProactiveStreamIntelligence()
                logger.info("[Nova] Proactive Stream Intelligence ready")

            elif module_name == "twitch":
                from .live.twitch_live import TwitchLivePlatform
                self.twitch = TwitchLivePlatform(channel_name="")
                logger.info("[Nova] Twitch bridge ready")

            elif module_name == "vrchat":
                from .live.vrchat_bridge import VRChatBridge
                self.vrchat = VRChatBridge()
                logger.info("[Nova] VRChat bridge ready")

            elif module_name == "p2p_federation":
                from .live.p2p_federation import VirtualAgencyP2PNode
                self.p2p_node = VirtualAgencyP2PNode()
                logger.info("[Nova] P2P Federation ready")

            elif module_name == "autonomous_raid":
                from .live.autonomous_raid_protocol import AutonomousRaidProtocol
                self.raid_protocol = AutonomousRaidProtocol(
                    node_id="nova_node", channel_name="nova_stream"
                )
                logger.info("[Nova] Autonomous Raid ready")

            elif module_name == "counter_troll":
                from .live.counter_troll_courtroom import CounterTrollCourtroom
                self.counter_troll = CounterTrollCourtroom()
                logger.info("[Nova] Counter Troll Courtroom ready")

            elif module_name == "in_character_mod":
                from .live.in_character_moderator import InCharacterModerator
                self.in_character_mod = InCharacterModerator()
                logger.info("[Nova] In-Character Moderator ready")

            elif module_name == "biometrics":
                from .biometrics.pulsoid_sync import BiometricStreamSync
                self.biometrics = BiometricStreamSync()
                logger.info("[Nova] Biometrics ready")

            elif module_name == "economy":
                from .economy import StreamLoyaltyEconomy
                self.economy = StreamLoyaltyEconomy()
                logger.info("[Nova] Stream Economy ready")

            elif module_name == "sponsorship":
                from .sponsorship import SponsorshipDirector
                self.sponsorship = SponsorshipDirector()
                logger.info("[Nova] Sponsorship ready")

            elif module_name == "studio":
                from .studio import StudioLightingManager, HighlightDetector
                self.studio_lighting = StudioLightingManager()
                self.highlight_detector = HighlightDetector()
                logger.info("[Nova] Studio ready")

            elif module_name == "vision":
                from .vision import ScreenWatcher
                self.screen_watcher = ScreenWatcher()
                logger.info("[Nova] Vision ready")

            elif module_name == "gaming":
                from .gaming import RetroMemoryAutomationBridge
                from .gaming.collab_pictionary import CollaborativePictionaryEngine
                self.retro_ram = RetroMemoryAutomationBridge()
                self.pictionary = CollaborativePictionaryEngine()
                logger.info("[Nova] Gaming ready")

            elif module_name == "spatial_world":
                from .gaming.spatial_world_model import SpatialWorldModel
                self.spatial_world = SpatialWorldModel()
                logger.info("[Nova] Spatial World ready")

            elif module_name == "vocal_ensemble":
                from .audio import (
                    RealtimeKaraokeHarmonizer,
                    NeuralVisemeCoarticulator,
                )
                self.karaoke = RealtimeKaraokeHarmonizer()
                self.viseme = NeuralVisemeCoarticulator()
                logger.info("[Nova] Vocal Ensemble ready")

            elif module_name == "vip_audio":
                from .audio.vip_audio_letter import VIPAudioLetterGenerator
                self.vip_audio = VIPAudioLetterGenerator()
                logger.info("[Nova] VIP Audio ready")

            else:
                logger.warning(f"[Nova] Unknown module: {module_name}")
                return

            self._initialized.add(module_name)
        except Exception as e:
            logger.warning(f"[Nova] Failed to init {module_name}: {e}")

    def __getattr__(self, name):
        """Lazy initialization for module access by name."""
        module_map = {
            "affective_engine": "affective_engine",
            "anchor_pipeline": "anchor_pipeline",
            "cognitive_router": "cognitive_router",
            "collab_squad": "collab_squad",
            "dual_track_router": "dual_track_router",
            "rap_battle": "rap_battle",
            "fan_memory": "fan_memory",
            "parasocial_crm": "parasocial_crm",
            "narrative_engine": "narrative",
            "stream_physics": "physics",
            "social_radar": "radar",
            "proactive_intelligence": "proactive",
            "twitch": "twitch",
            "vrchat": "vrchat",
            "p2p_node": "p2p_federation",
            "raid_protocol": "autonomous_raid",
            "counter_troll": "counter_troll",
            "in_character_mod": "in_character_mod",
            "biometrics": "biometrics",
            "economy": "economy",
            "sponsorship": "sponsorship",
            "studio_lighting": "studio",
            "highlight_detector": "studio",
            "screen_watcher": "vision",
            "retro_ram": "gaming",
            "pictionary": "gaming",
            "spatial_world": "spatial_world",
            "karaoke": "vocal_ensemble",
            "viseme": "vocal_ensemble",
            "vip_audio": "vip_audio",
        }
        if name in module_map:
            self._lazy_init(module_map[name])
            if name in self.__dict__:
                return self.__dict__[name]
        raise AttributeError(f"'{type(self).__name__}' has no attribute '{name}'")

    async def start(self):
        """Start all eager modules and background tasks."""
        self._running = True
        self._start_time = time.time()
        logger.info("[Nova] Engine started")

    async def stop(self):
        """Stop all running tasks and clean up."""
        self._running = False
        for task in self._tasks.values():
            task.cancel()
        self._tasks.clear()
        logger.info("[Nova] Engine stopped")

    @property
    def uptime_seconds(self) -> float:
        if self._start_time is None:
            return 0.0
        return time.time() - self._start_time

    def get_active_modules(self) -> Dict[str, bool]:
        """Returns dict of initialized modules and their availability."""
        return {m: m in self._initialized for m in sorted(self._initialized)}


def get_nova() -> NovaEngine:
    """Get or create the global NovaEngine singleton."""
    global _nova_engine
    if _nova_engine is None:
        _nova_engine = NovaEngine()
    return _nova_engine


_nova_engine: Optional[NovaEngine] = None
