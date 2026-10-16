"""
Real-Time Social Radar Engine for AI Influencers.
Scans trending gaming news and discussions to organically initiate contemporary banter.
"""
import aiohttp
import asyncio
import time
from dataclasses import dataclass
from typing import List, Optional
from loguru import logger


@dataclass
class TrendingTopic:
    source: str
    headline: str
    summary: str
    score: int
    url: str


class SocialRadarEngine:
    """
    Zero-cost social radar scanning public trending discussions.
    """
    def __init__(self):
        self.topic_buffer: List[TrendingTopic] = []
        self.headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AIInfluencerRadar/2.0"}
        self.last_fetch_time = 0.0

    async def fetch_reddit_trends(self, subreddit: str = "gaming", limit: int = 10) -> int:
        url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit={limit}"
        count = 0
        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get(url, timeout=4.0) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        for child in data.get("data", {}).get("children", []):
                            post = child.get("data", {})
                            if not post.get("over_18", False) and post.get("score", 0) > 300:
                                self.topic_buffer.append(TrendingTopic(
                                    source=f"r/{subreddit}",
                                    headline=post.get("title", ""),
                                    summary=post.get("selftext", "")[:200],
                                    score=post.get("score", 0),
                                    url=post.get("url", "")
                                ))
                                count += 1
                        logger.info(f"SocialRadar: Fetched {count} trending topics from r/{subreddit}")
        except Exception as e:
            logger.debug(f"SocialRadar: Could not fetch from r/{subreddit}: {e}")
        return count

    def pop_top_seed_prompt(self) -> Optional[str]:
        """Returns the top trending topic formatted as a conversational trigger."""
        if not self.topic_buffer:
            # Fallback trending gaming topic if offline
            return (
                "[SPONTANEOUS SOCIAL RADAR TOPIC]\n"
                "Source: Gaming News\n"
                "Headline: The latest patch broke game balance again\n"
                "Directive: Bring up how developers always nerf the most fun weapons in games and ask chat what their favorite overpowered weapon was."
            )

        self.topic_buffer.sort(key=lambda x: x.score, reverse=True)
        topic = self.topic_buffer.pop(0)
        return (
            f"[SPONTANEOUS SOCIAL RADAR TOPIC]\n"
            f"Source: {topic.source}\n"
            f"Headline: \"{topic.headline}\"\n"
            f"Directive: Bring this trending topic up casually to chat as if you just saw it on your second monitor. Give your hot take and ask chat's opinion!"
        )
