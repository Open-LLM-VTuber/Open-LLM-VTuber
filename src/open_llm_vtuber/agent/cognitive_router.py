# src/open_llm_vtuber/agent/cognitive_router.py
"""
Dynamic Multi-Model Cognitive Router.

Routes incoming streamer inputs and chat messages based on computed cognitive complexity:
- Simple banter, greetings, single-word reactions -> Ultra-fast 0.5B draft model (TTFT < 15ms)
- Deep questions, tactical gameplay dilemmas, lore debates -> 7B/70B reasoning model

Operates entirely locally on CPU with <1.0 ms heuristic evaluation overhead.
"""

import math
import re
import time
from collections import Counter
from dataclasses import dataclass


@dataclass
class RoutingDecision:
    target_model: str         # "DRAFT_0_5B" or "DEEP_7B"
    complexity_score: float   # 0.0 to 1.0
    reason: str
    evaluation_time_ms: float


class DynamicCognitiveRouter:
    """
    Sub-millisecond Heuristic and Entropy-based Cognitive Router.
    """

    def __init__(self, complexity_threshold: float = 0.42):
        self.threshold = complexity_threshold
        self.interrogative_regex = re.compile(
            r"^(why|how|what if|explain|should we|do you think|what is|tell me about|analyze)",
            re.IGNORECASE,
        )
        self.reflex_regex = re.compile(
            r"^(lol|lmao|gg|pog|poggers|hi|hello|hey|bye|o7|wtf|rip|nice|w|l|yes|no|yep|nope|sure|ok|k|cool)[!?.]*$",
            re.IGNORECASE,
        )

    def compute_shannon_entropy(self, text: str) -> float:
        """Calculates Shannon entropy of text character distribution."""
        if not text:
            return 0.0
        counts = Counter(text.lower())
        total = len(text)
        return -sum((c / total) * math.log2(c / total) for c in counts.values())

    def route_query(self, user_input: str) -> RoutingDecision:
        """
        Evaluates input complexity and dispatches to appropriate model tier.
        Latency ceiling: < 1.0 ms on pure CPU.
        """
        t0 = time.perf_counter()
        clean_text = user_input.strip()

        # Immediate Reflex Bypass (< 0.05 ms)
        if self.reflex_regex.match(clean_text):
            dt_ms = (time.perf_counter() - t0) * 1000.0
            return RoutingDecision(
                target_model="DRAFT_0_5B",
                complexity_score=0.05,
                reason="Reflexive Banter / Slang Match",
                evaluation_time_ms=round(dt_ms, 3),
            )

        words = clean_text.split()
        word_count = len(words)

        # Feature Scoring
        length_score = min(1.0, word_count / 18.0)
        entropy = min(1.0, self.compute_shannon_entropy(clean_text) / 4.5)
        is_question = 1.0 if (self.interrogative_regex.search(clean_text) or "?" in clean_text) else 0.0

        # Semantic complexity signals
        has_code = 1.0 if re.search(r"\{|\}|def |class |import |function|=>|async|await", clean_text) else 0.0
        has_url = 1.0 if re.search(r"https?://", clean_text) else 0.0
        has_numbers = 1.0 if re.search(r"\d+\.\d+|\d+\s*(percent|%|ms|s|mb|kb)", clean_text, re.I) else 0.0

        # Weighted cognitive complexity
        complexity = (0.25 * length_score) + (0.20 * entropy) + (0.30 * is_question) + (0.08 * has_code) + (0.08 * has_url) + (0.09 * has_numbers)
        complexity = min(1.0, max(0.0, complexity))

        if complexity < self.threshold:
            target = "DRAFT_0_5B"
            reason = f"Low Complexity Score ({complexity:.2f} < {self.threshold:.2f})"
        else:
            target = "DEEP_7B"
            reason = f"High Complexity / Cognitive Reasoning Required ({complexity:.2f} >= {self.threshold:.2f})"

        dt_ms = (time.perf_counter() - t0) * 1000.0
        return RoutingDecision(
            target_model=target,
            complexity_score=round(complexity, 3),
            reason=reason,
            evaluation_time_ms=round(dt_ms, 3),
        )


if __name__ == "__main__":
    router = DynamicCognitiveRouter()
    test_queries = [
        "lol",
        "gg chat",
        "Why do you think the boss adopted that particular attack pattern in phase 2?",
        "what if we build the nether portal underground?",
        "poggers!!",
        "Explain the thermodynamic implications of entropy in stellar nucleosynthesis.",
    ]

    for q in test_queries:
        dec = router.route_query(q)
        print(f"Query: \"{q}\" -> {dec.target_model} (Score: {dec.complexity_score}, Eval: {dec.evaluation_time_ms}ms, Reason: {dec.reason})")
