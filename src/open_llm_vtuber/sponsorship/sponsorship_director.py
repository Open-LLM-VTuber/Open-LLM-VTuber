"""
Autonomous Sponsorship & Dynamic Product Placement Engine.
Weaves contextual sponsor mentions into natural dialogue during relevant stream moments.
"""
import time
from dataclasses import dataclass
from typing import List, Optional
from loguru import logger


@dataclass
class SponsorCampaign:
    brand_name: str
    promo_code: str
    discount: str
    trigger_keywords: List[str]
    cooldown_seconds: int = 1800  # 30 minutes
    last_triggered: float = 0.0


class SponsorshipDirector:
    """
    Opportunistic brand integration manager for stream broadcasts.
    """
    def __init__(self):
        self.campaigns: List[SponsorCampaign] = [
            SponsorCampaign(
                brand_name="GamerSupps",
                promo_code="MILI20",
                discount="10%",
                trigger_keywords=["tired", "exhausted", "low stamina", "need energy", "thirsty", "sleepy"]
            ),
            SponsorCampaign(
                brand_name="Secretlab",
                promo_code="MILI_CHAIR",
                discount="$30",
                trigger_keywords=["back hurts", "sitting too long", "uncomfortable", "posture"]
            )
        ]

    def evaluate_opportunity(self, context_text: str) -> Optional[str]:
        now = time.time()
        lower_context = context_text.lower()

        for camp in self.campaigns:
            if now - camp.last_triggered > camp.cooldown_seconds:
                if any(kw in lower_context for kw in camp.trigger_keywords):
                    camp.last_triggered = now
                    prompt = (
                        f"[NATURAL SPONSORSHIP OPPORTUNITY: {camp.brand_name.upper()}]\n"
                        f"Brand: {camp.brand_name}\n"
                        f"Discount Code: {camp.promo_code} ({camp.discount} off)\n"
                        f"Directive: Casually and humorously weave a 1-sentence plug for {camp.brand_name} with your code {camp.promo_code} "
                        f"into your response. Make it self-aware, sarcastic, and completely natural to what just happened. Do NOT sound like an infomercial."
                    )
                    logger.info(f"Sponsorship Opportunity Triggered for: {camp.brand_name}")
                    return prompt
        return None
