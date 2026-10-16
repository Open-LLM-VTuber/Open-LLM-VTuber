"""
Two-Tier Real-Time Screen Perception Engine for AI VTuber & Influencer presence.
Uses low-overhead screen capture to detect game/desktop events with <1ms CPU cost,
triggering spontaneous commentary and reactions without constant Vision LLM streaming.
"""
import time
import threading
import numpy as np
from typing import Callable, Optional, Tuple, Dict, Any
from loguru import logger

try:
    import mss
    MSS_AVAILABLE = True
except ImportError:
    MSS_AVAILABLE = False


class ScreenWatcher:
    """
    Monitors desktop / game displays for visual events.
    """
    def __init__(
        self,
        event_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None,
        monitor_index: int = 1,
        poll_interval: float = 0.5,
        flash_threshold: float = 65.0
    ):
        if not MSS_AVAILABLE:
            raise ImportError("mss library is required for ScreenWatcher. Run: uv add mss")

        self.event_callback = event_callback
        self.monitor_index = monitor_index
        self.poll_interval = poll_interval
        self.flash_threshold = flash_threshold

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._prev_luminance: Optional[float] = None
        self._prev_frame_downscaled: Optional[np.ndarray] = None
        self._last_event_time = 0.0
        self._cooldown_seconds = 8.0  # Cooldown between spontaneous screen reactions

    def start(self):
        """Start screen watcher background polling loop."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        logger.info(f"ScreenWatcher started on monitor {self.monitor_index} (polling every {self.poll_interval}s)")

    def stop(self):
        """Stop screen watcher loop."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        logger.info("ScreenWatcher stopped.")

    def _loop(self):
        with mss.mss() as sct:
            monitors = sct.monitors
            mon = monitors[self.monitor_index] if len(monitors) > self.monitor_index else monitors[0]

            while self._running:
                try:
                    t0 = time.time()
                    raw_img = sct.grab(mon)
                    # Convert to RGB numpy array and downscale for micro-heuristic evaluation
                    frame = np.array(raw_img)[:, :, :3]  # Drop alpha
                    # Fast downsample 8x
                    small_frame = frame[::8, ::8, :]

                    # 1. Luminance calculation (Y = 0.299R + 0.587G + 0.114B)
                    lum = float(np.mean(0.299 * small_frame[:, :, 2] + 0.587 * small_frame[:, :, 1] + 0.114 * small_frame[:, :, 0]))

                    now = time.time()
                    if self._prev_luminance is not None and (now - self._last_event_time > self._cooldown_seconds):
                        delta_lum = lum - self._prev_luminance
                        if delta_lum > self.flash_threshold:
                            self._trigger_event(
                                "JUMPSCARE_OR_FLASH",
                                {
                                    "prompt": "[GAME REACTION]: The screen suddenly flashed brightly or a jumpscare just appeared! React with genuine shock, surprise, or panic!",
                                    "delta_luminance": delta_lum
                                }
                            )
                        elif delta_lum < -self.flash_threshold:
                            self._trigger_event(
                                "SCREEN_BLACKOUT_OR_DEATH",
                                {
                                    "prompt": "[GAME REACTION]: The screen suddenly plunged into darkness! Express confusion or wonder if your character just died or blacked out!",
                                    "delta_luminance": delta_lum
                                }
                            )

                    # 2. Perceptual frame shift
                    if self._prev_frame_downscaled is not None and (now - self._last_event_time > self._cooldown_seconds):
                        diff = np.mean(np.abs(small_frame.astype(np.int16) - self._prev_frame_downscaled.astype(np.int16)))
                        # Significant visual scene change (> 45 average pixel shift)
                        if diff > 45.0:
                            self._trigger_event(
                                "SCENE_SHIFT",
                                {
                                    "prompt": "[GAME REACTION]: A brand new visual scene or cutscene just loaded on the screen! Comment on what just happened on stream!",
                                    "scene_diff": float(diff)
                                }
                            )

                    self._prev_luminance = lum
                    self._prev_frame_downscaled = small_frame

                    # Sleep remaining interval
                    elapsed = time.time() - t0
                    sleep_time = max(0.01, self.poll_interval - elapsed)
                    time.sleep(sleep_time)

                except Exception as e:
                    logger.warning(f"ScreenWatcher error in polling loop: {e}")
                    time.sleep(self.poll_interval)

    def _trigger_event(self, event_name: str, payload: Dict[str, Any]):
        self._last_event_time = time.time()
        logger.info(f"ScreenWatcher triggered event: {event_name}")
        if self.event_callback:
            try:
                self.event_callback(event_name, payload)
            except Exception as e:
                logger.error(f"Error executing ScreenWatcher event callback: {e}")
