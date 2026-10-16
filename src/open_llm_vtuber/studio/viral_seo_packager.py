# src/open_llm_vtuber/studio/viral_seo_packager.py
"""
Viral Shorts SEO & Packaging Engine
Generates high-CTR curiosity-gap titles, first-3-second hook overlays,
multi-platform hashtag taxonomies, and thumbnail text graphics for automated clip distribution.
"""

import re
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from loguru import logger
from PIL import Image, ImageDraw, ImageFont


@dataclass
class ClipSEOProfile:
    clip_id: str
    original_topic: str
    virality_score: float  # 0.0 - 100.0
    curiosity_titles: List[str]
    hook_overlay_text: str
    badge_callout: str
    youtube_shorts_meta: Dict[str, Any]
    tiktok_meta: Dict[str, Any]
    instagram_reels_meta: Dict[str, Any]
    recommended_thumbnail_layout: Dict[str, Any]


class ViralShortsSEOPackager:
    """
    Automates the content packaging pipeline for viral short-form syndication.
    Transforms raw stream highlights into optimized multi-platform uploads.
    """

    HOOK_TEMPLATES = [
        "SHE ACTUALLY SAID THIS LIVE ON STREAM?! 💀",
        "Wait till the ending... I WAS NOT READY 😭",
        "Never ask an AI VTuber about this...",
        "The moment my chat completely BROKE me...",
        "I ACCIDENTALLY EXPOSED MY ENTIRE CODEBASE?!",
        "Chat made me do the UNFORGIVABLE 😱",
        "Is this the craziest glitch in stream history?!"
    ]

    BADGE_PRESETS = [
        "🚨 EMOTIONAL DAMAGE",
        "🔥 1000 IQ PLAY",
        "💀 CHAT IS COOKED",
        "⚠️ SHE SNAPPED",
        "✨ UNHINGED AI MOMENT"
    ]

    def __init__(self):
        logger.info("ViralShortsSEOPackager initialized.")

    def package_clip(
        self,
        clip_id: str,
        topic: str,
        transcript_snippet: str,
        peak_decibels: float = -3.0,
        emotional_intensity: float = 0.85
    ) -> ClipSEOProfile:
        """
        Synthesizes a complete algorithmic distribution package for a clip.
        """
        t0 = time.perf_counter()

        # Calculate Virality Score based on acoustic peak, emotional intensity, and transcript keywords
        intensity_score = min(1.0, emotional_intensity) * 40.0
        decibel_score = min(1.0, max(0.0, (peak_decibels + 30.0) / 30.0)) * 30.0
        
        has_exclamation = float(len(re.findall(r'[!?]', transcript_snippet))) * 4.0
        keyword_bonus = 15.0 if any(k in transcript_snippet.lower() for k in ["chat", "no way", "what", "omg", "die", "win", "ban"]) else 5.0
        virality_score = min(99.5, round(intensity_score + decibel_score + min(15.0, has_exclamation) + keyword_bonus, 1))

        # Generate Curiosity-Gap Titles
        sanitized_topic = topic.strip().title()
        titles = [
            f"The Moment {sanitized_topic} Went Completely Out of Control 💀",
            f"Why You NEVER Let Chat Control {sanitized_topic}...",
            f"My AI Brain Stopped Working During {sanitized_topic} 😭",
            f"She Lost Her Entire Mind Over {sanitized_topic}!",
            f"Wait For It... The Ending of {sanitized_topic} Changed Everything"
        ]

        # Primary Hook & Badge
        hook_text = self.HOOK_TEMPLATES[hash(clip_id) % len(self.HOOK_TEMPLATES)]
        badge = self.BADGE_PRESETS[hash(topic) % len(self.BADGE_PRESETS)]

        # Hashtag taxonomies
        core_tags = ["#VTuber", "#AIStreamer", "#AIVTuber", "#TwitchClips", "#FunnyMoments"]
        yt_tags = core_tags + ["#Shorts", "#Gaming", f"#{sanitized_topic.replace(' ', '')}"]
        tiktok_tags = core_tags + ["#fyp", "#foryou", "#viral", "#streamer"]
        reels_tags = core_tags + ["#reelsvideo", "#instareels", "#tech"]

        # Thumbnail layout configuration (9:16 vertical shorts format: 1080x1920)
        thumb_layout = {
            "canvas_width": 1080,
            "canvas_height": 1920,
            "primary_headline": hook_text,
            "font_size": 72,
            "font_color": "#FFFF00",  # High-CTR yellow
            "stroke_color": "#000000",
            "stroke_width": 8,
            "badge": badge,
            "badge_color": "#FF0055",
            "safe_zone_y_top": 350,
            "safe_zone_y_bottom": 1400
        }

        profile = ClipSEOProfile(
            clip_id=clip_id,
            original_topic=topic,
            virality_score=virality_score,
            curiosity_titles=titles,
            hook_overlay_text=hook_text,
            badge_callout=badge,
            youtube_shorts_meta={
                "title": titles[0][:100],
                "description": f"{transcript_snippet}\n\nSubscribe for daily unhinged AI moments!\n{' '.join(yt_tags)}",
                "tags": [t.strip("#") for t in yt_tags],
                "category_id": "20",  # Gaming
            },
            tiktok_meta={
                "caption": f"{titles[1][:80]} {' '.join(tiktok_tags)}",
                "allow_duet": True,
                "allow_stitch": True
            },
            instagram_reels_meta={
                "caption": f"{titles[2][:80]}\n.\n.\n{' '.join(reels_tags)}",
                "share_to_feed": True
            },
            recommended_thumbnail_layout=thumb_layout
        )

        elapsed = (time.perf_counter() - t0) * 1000.0
        logger.debug(f"Packaged clip {clip_id} with virality score {virality_score} in {elapsed:.2f}ms")
        return profile

    def render_sample_thumbnail_card(
        self,
        profile: ClipSEOProfile,
        width: int = 540,
        height: int = 960
    ) -> Image.Image:
        """
        Renders a fast preview image card of the vertical thumbnail layout using Pillow.
        Zero external cost, fully local.
        """
        img = Image.new("RGB", (width, height), color=(20, 15, 30))
        draw = ImageDraw.Draw(img)

        # Draw decorative background gradient/lines
        for y in range(0, height, 40):
            draw.line([(0, y), (width, y)], fill=(35, 25, 55), width=1)

        # Draw Badge banner
        badge_y = int(height * 0.22)
        draw.rectangle([(30, badge_y), (width - 30, badge_y + 45)], fill=(255, 0, 85))
        draw.text((50, badge_y + 12), profile.badge_callout, fill=(255, 255, 255))

        # Draw Headline text block
        headline_y = int(height * 0.32)
        words = profile.hook_overlay_text.split()
        lines = []
        cur_line = []
        for w in words:
            cur_line.append(w)
            if len(" ".join(cur_line)) > 16:
                lines.append(" ".join(cur_line))
                cur_line = []
        if cur_line:
            lines.append(" ".join(cur_line))

        line_offset = headline_y
        for line in lines[:3]:
            # Stroke simulation
            for dx in [-2, 0, 2]:
                for dy in [-2, 0, 2]:
                    draw.text((40 + dx, line_offset + dy), line, fill=(0, 0, 0))
            draw.text((40, line_offset), line, fill=(255, 255, 0))
            line_offset += 45

        # Footer stats
        footer_text = f"Predicted Virality: {profile.virality_score}% | Open-LLM-VTuber Shorts"
        draw.text((40, height - 60), footer_text, fill=(180, 180, 210))

        return img
