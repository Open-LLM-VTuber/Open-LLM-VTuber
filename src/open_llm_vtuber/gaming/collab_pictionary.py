# src/open_llm_vtuber/gaming/collab_pictionary.py
"""
Collaborative Pictionary & Vector Sketch Evaluation Engine
Enables real-time multi-VTuber collaborative drawing, chat sketch guessing,
and procedural stroke generation with geometric sketch recognition heuristics.
"""

import time
import math
import random
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from loguru import logger


@dataclass
class StrokePoint:
    x: float  # 0.0 to 1.0 normalized canvas coordinate
    y: float  # 0.0 to 1.0 normalized canvas coordinate
    timestamp_ms: float
    pressure: float = 1.0


@dataclass
class VectorStroke:
    stroke_id: int
    color_hex: str
    brush_width: float
    points: List[StrokePoint] = field(default_factory=list)


@dataclass
class PictionaryRound:
    round_id: str
    target_word: str
    drawer: str
    time_limit_sec: float
    start_time: float
    is_active: bool = True
    solved_by: Optional[str] = None
    strokes: List[VectorStroke] = field(default_factory=list)


class CollaborativePictionaryEngine:
    """
    Manages vector drawing sessions, procedural sketch drawing by the AI VTuber,
    and heuristic evaluation of incoming player/chat sketches.
    """

    CONCEPT_TEMPLATES = {
        "house": [
            # Roof triangle
            [(0.2, 0.5), (0.5, 0.2), (0.8, 0.5)],
            # Walls
            [(0.25, 0.5), (0.25, 0.85), (0.75, 0.85), (0.75, 0.5)],
            # Door
            [(0.42, 0.85), (0.42, 0.65), (0.58, 0.65), (0.58, 0.85)],
        ],
        "cat": [
            # Head circle approx
            [(0.35, 0.5), (0.5, 0.35), (0.65, 0.5), (0.5, 0.65), (0.35, 0.5)],
            # Left ear
            [(0.38, 0.4), (0.32, 0.25), (0.44, 0.36)],
            # Right ear
            [(0.56, 0.36), (0.68, 0.25), (0.62, 0.4)],
            # Whiskers
            [(0.3, 0.52), (0.2, 0.50)],
            [(0.7, 0.52), (0.8, 0.50)],
        ],
        "sun": [
            # Core circle
            [(0.4, 0.5), (0.5, 0.4), (0.6, 0.5), (0.5, 0.6), (0.4, 0.5)],
            # Rays
            [(0.5, 0.35), (0.5, 0.2)],
            [(0.5, 0.65), (0.5, 0.8)],
            [(0.35, 0.5), (0.2, 0.5)],
            [(0.65, 0.5), (0.8, 0.5)],
        ],
        "heart": [
            # Top lobes to bottom point
            [(0.5, 0.4), (0.35, 0.25), (0.22, 0.4), (0.5, 0.75), (0.78, 0.4), (0.65, 0.25), (0.5, 0.4)]
        ]
    }

    def __init__(self):
        self.active_round: Optional[PictionaryRound] = None
        self.scores: Dict[str, int] = {}
        logger.info("CollaborativePictionaryEngine initialized.")

    def start_round(
        self,
        word: str,
        drawer: str = "AI_VTuber",
        time_limit_sec: float = 60.0
    ) -> PictionaryRound:
        """Starts a new collaborative pictionary round."""
        rnd = PictionaryRound(
            round_id=f"rnd_{int(time.time() * 1000)}",
            target_word=word.strip().lower(),
            drawer=drawer,
            time_limit_sec=time_limit_sec,
            start_time=time.time(),
            is_active=True
        )
        self.active_round = rnd
        logger.info(f"Pictionary round {rnd.round_id} started. Word: '{word}', Drawer: {drawer}")
        return rnd

    def generate_procedural_sketch(
        self,
        concept: str,
        color_hex: str = "#FF4081",
        brush_width: float = 4.0
    ) -> List[VectorStroke]:
        """
        Generates vector strokes for a given concept with simulated human hand-drawn jitter.
        """
        key = concept.strip().lower()
        paths = self.CONCEPT_TEMPLATES.get(key, self.CONCEPT_TEMPLATES["heart"])
        strokes = []

        stroke_idx = 1
        for poly in paths:
            stroke = VectorStroke(stroke_id=stroke_idx, color_hex=color_hex, brush_width=brush_width)
            t_ms = 0.0
            
            for pt_idx in range(len(poly) - 1):
                p_start = poly[pt_idx]
                p_end = poly[pt_idx + 1]
                steps = 6
                for s in range(steps + 1):
                    alpha = s / steps
                    # Linear interpolation with slight organic jitter
                    x = p_start[0] + (p_end[0] - p_start[0]) * alpha + random.uniform(-0.005, 0.005)
                    y = p_start[1] + (p_end[1] - p_start[1]) * alpha + random.uniform(-0.005, 0.005)
                    stroke.points.append(
                        StrokePoint(
                            x=round(x, 4),
                            y=round(y, 4),
                            timestamp_ms=round(t_ms, 1),
                            pressure=round(random.uniform(0.85, 1.0), 2)
                        )
                    )
                    t_ms += 35.0

            strokes.append(stroke)
            stroke_idx += 1

        if self.active_round and self.active_round.is_active:
            self.active_round.strokes.extend(strokes)

        return strokes

    def evaluate_guess(self, chatter_name: str, guess_text: str) -> Dict[str, Any]:
        """Evaluates a chatter's guess against the active target word."""
        if not self.active_round or not self.active_round.is_active:
            return {"status": "NO_ACTIVE_ROUND", "correct": False}

        elapsed = time.time() - self.active_round.start_time
        if elapsed > self.active_round.time_limit_sec:
            self.active_round.is_active = False
            return {"status": "TIME_EXPIRED", "correct": False}

        sanitized_guess = guess_text.strip().lower()
        target = self.active_round.target_word

        if sanitized_guess == target or target in sanitized_guess:
            # Correct guess!
            points_awarded = max(10, int((self.active_round.time_limit_sec - elapsed) * 2.0))
            self.scores[chatter_name] = self.scores.get(chatter_name, 0) + points_awarded
            self.active_round.is_active = False
            self.active_round.solved_by = chatter_name

            return {
                "status": "CORRECT_GUESS",
                "correct": True,
                "winner": chatter_name,
                "word": target,
                "points": points_awarded,
                "total_score": self.scores[chatter_name],
                "time_taken_sec": round(elapsed, 2)
            }
        else:
            # Check near miss (levenshtein or substring)
            is_close = any(w in sanitized_guess for w in target.split()) or len(target) > 3 and target[:3] in sanitized_guess
            return {
                "status": "INCORRECT_GUESS",
                "correct": False,
                "chatter": chatter_name,
                "is_close": is_close,
                "hint": f"Close! Word has {len(target)} letters." if is_close else None
            }

    def serialize_strokes_to_svg(self, strokes: List[VectorStroke], width: int = 400, height: int = 400) -> str:
        """Serializes vector strokes to SVG format for OBS or browser overlays."""
        svg_parts = [f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">']
        for stroke in strokes:
            if not stroke.points:
                continue
            path_d = []
            for i, pt in enumerate(stroke.points):
                px = pt.x * width
                py = pt.y * height
                cmd = "M" if i == 0 else "L"
                path_d.append(f"{cmd} {px:.1f} {py:.1f}")
            d_str = " ".join(path_d)
            svg_parts.append(
                f'<path d="{d_str}" stroke="{stroke.color_hex}" stroke-width="{stroke.brush_width}" fill="none" stroke-linecap="round" stroke-linejoin="round"/>'
            )
        svg_parts.append('</svg>')
        return "\n".join(svg_parts)
