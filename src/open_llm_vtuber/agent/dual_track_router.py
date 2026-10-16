"""
Nova AI Influencer — Groq LPU Dual-Track Router
================================================
Zero-cost intelligent routing between:
  - Local Ollama (fast, for banter / short reactions, <50ms TTFT)
  - Groq LPU free tier (for complex questions, research, multi-step reasoning)

The router analyzes the input to decide which backend to use.
Falls back gracefully to Ollama if Groq is rate-limited or unavailable.

Usage:
    router = DualTrackLLMRouter(
        ollama_model="babar_jamali/qwen3-1.7b-nolimits:latest",
        groq_api_key="gsk_..."  # Optional — system works without it
    )
    async for token in router.stream(user_input, system_prompt):
        print(token, end="")
"""

import os
import re
import time
from typing import AsyncIterator, Optional
from loguru import logger


# Thresholds for routing decisions
COMPLEX_WORD_THRESHOLD = 15    # Words count above which we may route to Groq
COMPLEXITY_SCORE_THRESHOLD = 3 # Score above which we route to Groq

COMPLEX_PATTERNS = [
    r"\b(explain|research|analyze|compare|summarize|write|code|script|debug|implement|design|build|create|develop|architecture|system|framework|algorithm|optimize|refactor|compile|deploy|configure)\b",
    r"\b(how does|why does|what is the|can you write|help me with|what are|how to|when should|where can|which one|is it|are there|do you know)\b",
    r"\b(according to|in detail|comprehensive|step by step|in depth|breakdown|overview|comparison|pros and cons|advantages|disadvantages)\b",
    r"\b(python|javascript|code|algorithm|math|calculate|formula|server|database|api|cloud|docker|kubernetes|rust|go|c\+\+|java|csharp|react|vue|angular|sql|graphql)\b",
]

BANTER_PATTERNS = [
    r"^(lol|haha|lmao|based|pog|kekw|w|l|gg|nice|cool|ok|okay|what|really|no way|same|fr|copium|simp|sigma|rizz|skibidi|gyatt|fanum|kai|caught|imagine|sussy|amogus|sus|emote|pepe|wow|sobs|huge|l\+\.+k|kek)\b",
    r"^.{1,15}$",
]


class DualTrackLLMRouter:
    """
    Routes queries between local Ollama and Groq LPU based on complexity.
    Falls back to Ollama if Groq is unavailable (no API key or rate limit).
    """

    def __init__(
        self,
        ollama_base_url: str = "http://localhost:11434/v1",
        ollama_model: str = "babar_jamali/qwen3-1.7b-nolimits:latest",
        groq_api_key: Optional[str] = None,
        groq_model: str = "llama-3.3-70b-versatile",
    ):
        self.ollama_base_url = ollama_base_url
        self.ollama_model = ollama_model
        self.groq_api_key = groq_api_key or os.environ.get("GROQ_API_KEY", "")
        self.groq_model = groq_model
        self._groq_available = bool(self.groq_api_key)
        self._groq_error_count = 0

        if self._groq_available:
            logger.info(f"DualTrackLLMRouter: Groq available (model: {groq_model})")
        else:
            logger.info("DualTrackLLMRouter: Running in Ollama-only mode (no GROQ_API_KEY)")

    def _compute_complexity_score(self, text: str) -> int:
        """
        Heuristic complexity scorer. Returns 0 (banter) to 5+ (complex).
        """
        score = 0
        lower = text.lower()

        # Check banter patterns first (short-circuit)
        for pattern in BANTER_PATTERNS:
            if re.match(pattern, lower):
                return 0

        # Word count
        word_count = len(text.split())
        if word_count > COMPLEX_WORD_THRESHOLD:
            score += 1
        if word_count > 30:
            score += 1

        # Complex intent keywords
        for pattern in COMPLEX_PATTERNS:
            if re.search(pattern, lower):
                score += 1

        # Question complexity
        if text.count("?") > 1:
            score += 1

        # Contains code-like patterns
        if any(c in text for c in ["{", "}", "def ", "class ", "import ", "```"]):
            score += 2

        return score

    def route(self, user_input: str) -> str:
        """
        Decide routing: returns 'groq' or 'ollama'.
        """
        score = self._compute_complexity_score(user_input)

        if (
            score >= COMPLEXITY_SCORE_THRESHOLD
            and self._groq_available
            and self._groq_error_count < 3
        ):
            logger.debug(f"DualTrackRouter: Routing to GROQ (complexity score: {score})")
            return "groq"
        else:
            logger.debug(f"DualTrackRouter: Routing to OLLAMA (complexity score: {score})")
            return "ollama"

    async def stream_ollama(
        self, user_input: str, system_prompt: str, messages: list = None
    ) -> AsyncIterator[str]:
        """Stream from local Ollama."""
        try:
            import httpx

            payload = {
                "model": self.ollama_model,
                "messages": (messages or []) + [{"role": "user", "content": user_input}],
                "stream": True,
                "temperature": 0.9,
            }
            if system_prompt:
                payload["messages"] = [
                    {"role": "system", "content": system_prompt}
                ] + (messages or []) + [{"role": "user", "content": user_input}]

            async with httpx.AsyncClient(timeout=60) as client:
                async with client.stream(
                    "POST",
                    f"{self.ollama_base_url}/chat/completions",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            chunk = line[6:].strip()
                            if chunk == "[DONE]":
                                break
                            try:
                                import json
                                data = json.loads(chunk)
                                delta = data["choices"][0]["delta"]
                                if "content" in delta:
                                    yield delta["content"]
                            except Exception:
                                continue
        except Exception as e:
            logger.error(f"Ollama streaming error: {e}")
            yield "[Ollama connection error — is Ollama running?]"

    async def stream_groq(
        self, user_input: str, system_prompt: str, messages: list = None
    ) -> AsyncIterator[str]:
        """Stream from Groq LPU (free tier)."""
        try:
            import httpx
            import json

            headers = {
                "Authorization": f"Bearer {self.groq_api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": self.groq_model,
                "messages": [{"role": "system", "content": system_prompt}]
                           + (messages or [])
                           + [{"role": "user", "content": user_input}],
                "stream": True,
                "temperature": 0.8,
                "max_tokens": 512,
            }

            async with httpx.AsyncClient(timeout=30) as client:
                async with client.stream(
                    "POST",
                    "https://api.groq.com/openai/v1/chat/completions",
                    json=payload,
                    headers=headers
                ) as response:
                    if response.status_code == 429:
                        logger.warning("Groq rate limited — falling back to Ollama")
                        self._groq_error_count += 1
                        # Fallback
                        async for token in self.stream_ollama(user_input, system_prompt, messages):
                            yield token
                        return

                    if response.status_code != 200:
                        logger.error(f"Groq error: {response.status_code}")
                        self._groq_error_count += 1
                        async for token in self.stream_ollama(user_input, system_prompt, messages):
                            yield token
                        return

                    self._groq_error_count = max(0, self._groq_error_count - 1)
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            chunk = line[6:].strip()
                            if chunk == "[DONE]":
                                break
                            try:
                                data = json.loads(chunk)
                                delta = data["choices"][0]["delta"]
                                if "content" in delta and delta["content"]:
                                    yield delta["content"]
                            except Exception:
                                continue

        except Exception as e:
            logger.error(f"Groq streaming error: {e} — falling back to Ollama")
            self._groq_error_count += 1
            async for token in self.stream_ollama(user_input, system_prompt, messages):
                yield token

    async def stream(
        self,
        user_input: str,
        system_prompt: str = "",
        messages: list = None
    ) -> AsyncIterator[str]:
        """
        Route and stream from the optimal backend.
        """
        backend = self.route(user_input)
        t0 = time.perf_counter()

        if backend == "groq":
            async for token in self.stream_groq(user_input, system_prompt, messages):
                yield token
        else:
            async for token in self.stream_ollama(user_input, system_prompt, messages):
                yield token

        elapsed = (time.perf_counter() - t0) * 1000
        logger.debug(f"DualTrackRouter: {backend.upper()} completed in {elapsed:.0f}ms")
