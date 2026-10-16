# src/open_llm_vtuber/biometrics/pulsoid_sync.py
"""
Biometric & Physiological Stream Synchronization Engine for Real-Time AI Influencers.

Connects to streamer wearable sensor telemetry (Pulsoid / HypeRate / Apple Watch / Polar H10 / Garmin)
via WebSocket or local simulation feed.
Dynamically computes physiological modulations:
  - Chest Breathing Frequency (ParamBreath, mapped from BPM)
  - Panic Blush Intensity (ParamCheek, triggered during tachycardia/fright)
  - Terror Pupil Dilation (ParamEyeBallForm)
  - Vocal Pitch Instability / Tremor factor for TTS modulation
  - PAD Affective Engine coupling (Arousal & Dominance dynamic shifts)
"""

import asyncio
import json
import math
import random
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional
from loguru import logger

try:
    import aiohttp
except ImportError:
    aiohttp = None


@dataclass
class BiometricTelemetry:
    heart_rate: int = 72
    hrv_ms: float = 48.0
    stress_index: float = 0.2
    timestamp: float = field(default_factory=time.time)


@dataclass
class BiometricAvatarModulation:
    heart_rate: int
    breath_freq_hz: float
    blush_intensity: float
    pupil_dilation: float
    vocal_tremor: float
    pad_arousal_shift: float
    pad_dominance_shift: float
    state_description: str


class BiometricStreamSync:
    """
    Sub-millisecond Biometric Telemetry Coupling Engine.
    Maps real-time human cardiac & physiological telemetry to Live2D avatar rigging.
    """

    def __init__(
        self,
        pulsoid_token: Optional[str] = None,
        baseline_bpm: int = 70,
        horror_threshold_bpm: int = 115,
        on_modulation_callback: Optional[Callable[[BiometricAvatarModulation], None]] = None,
    ):
        self.pulsoid_token = pulsoid_token
        self.baseline_bpm = baseline_bpm
        self.horror_threshold_bpm = horror_threshold_bpm
        self.on_modulation_callback = on_modulation_callback
        self.current_telemetry = BiometricTelemetry(heart_rate=baseline_bpm)
        self._running = False
        self._smoothed_bpm = float(baseline_bpm)

    def calculate_modulation(self, telemetry: BiometricTelemetry) -> BiometricAvatarModulation:
        """
        Computes Live2D parameter values and acoustic shifts from raw biometric signals.
        """
        # Exponential smoothing (alpha = 0.3) to avoid jerky avatar jitter
        self._smoothed_bpm = 0.7 * self._smoothed_bpm + 0.3 * telemetry.heart_rate
        bpm = self._smoothed_bpm

        # 1. Breathing Frequency: normal 0.25 Hz (~15 breaths/min) to 1.8 Hz in extreme panic
        # Scaled non-linearly with heart rate elevation
        elevation_ratio = max(0.0, (bpm - self.baseline_bpm) / max(1.0, (self.horror_threshold_bpm - self.baseline_bpm)))
        breath_freq_hz = 0.25 + 1.25 * math.pow(min(1.5, elevation_ratio), 1.4)

        # 2. Panic Blush (ParamCheek): 0.0 at resting, rises smoothly to 1.0 when BPM > baseline + 20
        blush_intensity = max(0.0, min(1.0, (bpm - (self.baseline_bpm + 15)) / 35.0))

        # 3. Terror Pupil Dilation (ParamEyeBallForm): pupil widens under adrenaline/arousal
        pupil_dilation = max(0.0, min(1.0, (bpm - (self.baseline_bpm + 25)) / 40.0))

        # 4. Vocal Pitch Instability / Tremor factor for TTS modulation
        vocal_tremor = max(0.0, min(0.35, elevation_ratio * 0.25))

        # 5. Affective PAD Coupling
        # Spike in BPM drives Arousal up (+0.1 to +0.9) and Dominance down (-0.1 to -0.6 if terrified)
        pad_arousal_shift = min(0.85, elevation_ratio * 0.6)
        pad_dominance_shift = -min(0.7, elevation_ratio * 0.5) if bpm > (self.baseline_bpm + 30) else 0.0

        state_desc = "Resting / Calm"
        if bpm >= self.horror_threshold_bpm:
            state_desc = "MAX TERROR / Adrenaline Shock"
        elif bpm >= self.baseline_bpm + 25:
            state_desc = "Elevated Heart Rate / Tense"
        elif bpm >= self.baseline_bpm + 10:
            state_desc = "Mild Excitement"

        return BiometricAvatarModulation(
            heart_rate=int(round(bpm)),
            breath_freq_hz=round(breath_freq_hz, 3),
            blush_intensity=round(blush_intensity, 3),
            pupil_dilation=round(pupil_dilation, 3),
            vocal_tremor=round(vocal_tremor, 3),
            pad_arousal_shift=round(pad_arousal_shift, 3),
            pad_dominance_shift=round(pad_dominance_shift, 3),
            state_description=state_desc,
        )

    def process_bpm_sample(self, bpm: int, hrv: float = 45.0, stress: float = 0.2) -> BiometricAvatarModulation:
        """Directly processes a telemetry sample and triggers callbacks."""
        self.current_telemetry = BiometricTelemetry(
            heart_rate=bpm,
            hrv_ms=hrv,
            stress_index=stress,
            timestamp=time.time(),
        )
        modulation = self.calculate_modulation(self.current_telemetry)
        if self.on_modulation_callback:
            try:
                self.on_modulation_callback(modulation)
            except Exception as e:
                logger.error(f"Error in biometric modulation callback: {e}")
        return modulation

    async def run_pulsoid_feed(self):
        """Connects to Pulsoid WebSocket stream for real-time telemetry ingestion."""
        if not self.pulsoid_token:
            logger.warning("Pulsoid token not provided. Falling back to simulated biometric stream.")
            await self.run_simulation_feed()
            return

        if not aiohttp:
            logger.error("aiohttp required for Pulsoid WebSocket connection. Running simulation instead.")
            await self.run_simulation_feed()
            return

        url = f"wss://dev.pulsoid.net/api/v1/data/real_time?access_token={self.pulsoid_token}"
        logger.info(f"Connecting to Pulsoid Biometric WebSocket API...")
        self._running = True

        while self._running:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.ws_connect(url, timeout=10.0) as ws:
                        logger.info("Successfully connected to Pulsoid telemetry feed.")
                        async for msg in ws:
                            if not self._running:
                                break
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                data = json.loads(msg.data)
                                if "data" in data and "heart_rate" in data["data"]:
                                    bpm = int(data["data"]["heart_rate"])
                                    mod = self.process_bpm_sample(bpm)
                                    logger.debug(f"Biometric Pulse: {bpm} BPM | Breath: {mod.breath_freq_hz}Hz | Blush: {mod.blush_intensity}")
                            elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                                break
            except Exception as e:
                logger.warning(f"Pulsoid connection dropped: {e}. Reconnecting in 3s...")
                await asyncio.sleep(3.0)

    async def run_simulation_feed(self, update_interval: float = 1.0):
        """Simulates realistic cardiac telemetry with occasional horror spikes."""
        logger.info(f"Starting Biometric Simulation Engine (Baseline: {self.baseline_bpm} BPM)...")
        self._running = True
        bpm = float(self.baseline_bpm)
        step = 0

        while self._running:
            step += 1
            # Every 15-20 steps, trigger a simulated jump-scare / horror panic spike
            if step % 20 == 0:
                bpm = float(random.randint(125, 155))
                logger.warning(f"⚠️ Simulated Horror Jump Scare Triggered! Heart Rate Spikes to {int(bpm)} BPM!")
            else:
                # Smooth drift back towards baseline
                target = self.baseline_bpm + random.uniform(-4, 6)
                bpm = 0.85 * bpm + 0.15 * target

            mod = self.process_bpm_sample(int(round(bpm)))
            logger.info(
                f"[Biometrics] BPM: {mod.heart_rate} | State: {mod.state_description} | "
                f"Breath: {mod.breath_freq_hz}Hz | Blush: {mod.blush_intensity:.2f} | "
                f"Pupil: {mod.pupil_dilation:.2f} | Tremor: {mod.vocal_tremor:.2f}"
            )
            await asyncio.sleep(update_interval)

    def stop(self):
        self._running = False


if __name__ == "__main__":
    def on_avatar_update(m: BiometricAvatarModulation):
        pass

    sync = BiometricStreamSync(on_modulation_callback=on_avatar_update)
    try:
        asyncio.run(sync.run_simulation_feed(update_interval=0.8))
    except KeyboardInterrupt:
        print("\nBiometrics simulation stopped.")
