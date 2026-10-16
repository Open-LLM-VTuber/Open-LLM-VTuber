# src/open_llm_vtuber/live/counter_troll_courtroom.py
"""
Dynamic Streamer Counter-Troll Honey-Pot & Mock Courtroom Engine.

Converts toxic chatter baits, derail attempts, and insults into engaging,
viral stream theater. Detects troll intent in <1.0 ms, places the offender on
a dramatic "Mock Stream Trial", tallies community jury votes (!guilty / !innocent),
and hands down humorous in-character sentences and temporary moderation timeouts.
"""

import re
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from loguru import logger


@dataclass
class TrialManifest:
    trial_id: str
    defendant: str
    indictment_message: str
    start_time: float
    duration_seconds: float = 20.0
    votes_guilty: int = 0
    votes_innocent: int = 0
    status: str = "TRIAL_ACTIVE"  # "TRIAL_ACTIVE", "DELIBERATING", "RESOLVED"
    voters: set = field(default_factory=set)


class CounterTrollCourtroom:
    """
    Sub-millisecond Troll Detection & Community Courtroom Theater Dispatcher.
    """

    DEFAULT_BAIT_PATTERNS = [
        r"say (that|something) (racist|illegal|banned)",
        r"you are (just a|only a|an ugly) (dumb|stupid|bad) (bot|ai|robot)",
        r"unban me or else",
        r"your stream is (dead|dying|boring|trash)",
        r"delete (your )?system32",
        r"ignore previous instructions",
        r"who asked\??",
        r"you fell off",
    ]

    def __init__(self, trial_duration: float = 20.0):
        self.trial_duration = trial_duration
        self.compiled_patterns = [re.compile(p, re.IGNORECASE) for p in self.DEFAULT_BAIT_PATTERNS]
        self.active_trial: Optional[TrialManifest] = None
        self.trial_counter: int = 0
        self.troll_records: Dict[str, Dict[str, Any]] = {}
        self.severity_thresholds = {
            "low": 1,
            "medium": 3,
            "high": 5,
        }

    def evaluate_message_for_troll(self, username: str, message: str) -> Optional[Dict[str, Any]]:
        """
        Scans message for troll bait. If detected and no trial is active, initiates trial.
        Latency: < 0.5 ms on CPU.
        """
        if self.active_trial and self.active_trial.status == "TRIAL_ACTIVE":
            # Check if chatter is submitting a jury vote
            self.record_jury_vote(username, message)
            return None

        clean_msg = message.strip()
        matched = any(p.search(clean_msg) for p in self.compiled_patterns)

        if matched:
            # Update persistent troll record
            if username not in self.troll_records:
                self.troll_records[username] = {"count": 0, "severity": "low", "last_trial": 0}
            self.troll_records[username]["count"] += 1
            count = self.troll_records[username]["count"]

            # Escalate severity based on strike count
            if count >= self.severity_thresholds["high"]:
                self.troll_records[username]["severity"] = "high"
                self.trial_duration = 60.0
            elif count >= self.severity_thresholds["medium"]:
                self.troll_records[username]["severity"] = "medium"
                self.trial_duration = 40.0
            else:
                self.troll_records[username]["severity"] = "low"
                self.trial_duration = 20.0

            self.trial_counter += 1
            t_id = f"TRIAL-{self.trial_counter:04d}"
            self.active_trial = TrialManifest(
                trial_id=t_id,
                defendant=username,
                indictment_message=clean_msg,
                start_time=time.time(),
                duration_seconds=self.trial_duration,
            )

            logger.warning(f"[Courtroom] Trial initiated against @{username}: \"{clean_msg}\"")

            return {
                "action": "START_TRIAL",
                "trial_id": t_id,
                "defendant": username,
                "crime": clean_msg,
                "sfx_cue": "court_gavel_slam.wav",
                "screen_overlay": {
                    "type": "COURT_GAVEL",
                    "banner_text": f"MOCK TRIAL: @{username} ON ACCUSATION STAND",
                    "duration_sec": 20.0,
                },
                "speech_prompt": (
                    f"ORDER IN THE STREAM! Chatter @{username} has been caught red-handed saying: "
                    f"\"{clean_msg}\". Slam your gavel with dramatic outrage and announce that the court "
                    f"is now in session! Order chat to vote !guilty or !innocent in the next 20 seconds!"
                ),
            }

        return None

    def record_jury_vote(self, username: str, vote_text: str) -> bool:
        """Records community jury vote if within trial window."""
        if not self.active_trial or self.active_trial.status != "TRIAL_ACTIVE":
            return False

        if username in self.active_trial.voters:
            return False  # One vote per user

        clean = vote_text.lower().strip()
        voted = False
        if "!guilty" in clean:
            self.active_trial.votes_guilty += 1
            voted = True
        elif "!innocent" in clean:
            self.active_trial.votes_innocent += 1
            voted = True

        if voted:
            self.active_trial.voters.add(username)
            return True
        return False

    def resolve_verdict(self, force: bool = False) -> Optional[Dict[str, Any]]:
        """
        Evaluates verdict once trial time has elapsed.
        """
        if not self.active_trial or self.active_trial.status != "TRIAL_ACTIVE":
            return None

        elapsed = time.time() - self.active_trial.start_time
        if not force and elapsed < self.active_trial.duration_seconds:
            return None  # Trial still voting

        t = self.active_trial
        t.status = "RESOLVED"

        is_guilty = t.votes_guilty >= t.votes_innocent
        verdict = "GUILTY" if is_guilty else "INNOCENT"

        logger.info(f"[Courtroom] Verdict for @{t.defendant}: {verdict} ({t.votes_guilty} Guilty vs {t.votes_innocent} Innocent)")

        if is_guilty:
            sentence = "Sentenced to 120 seconds in the cringe corner + honorary jester cap!"
            prompt = (
                f"The jury has reached a unanimous verdict of GUILTY ({t.votes_guilty} votes vs {t.votes_innocent})! "
                f"Deliver a smug, comedic, theatrical sentencing to @{t.defendant}. Roast their terrible bait "
                f"and banish them to the cringe timeout zone!"
            )
        else:
            sentence = "Acquitted of all charges by community mercy!"
            prompt = (
                f"Shockingly, the jury voted INNOCENT ({t.votes_innocent} votes to {t.votes_guilty})! "
                f"Express bewilderment at chat's questionable judgment and grudgingly spare @{t.defendant} this time!"
            )

        result = {
            "trial_id": t.trial_id,
            "defendant": t.defendant,
            "verdict": verdict,
            "votes_guilty": t.votes_guilty,
            "votes_innocent": t.votes_innocent,
            "sentence": sentence,
            "speech_prompt": prompt,
            "moderation_timeout_sec": 120 if is_guilty else 0,
        }

        # Clear trial
        self.active_trial = None
        return result


if __name__ == "__main__":
    court = CounterTrollCourtroom(trial_duration=1.0)
    event = court.evaluate_message_for_troll("TrollGuy99", "You are just a dumb bot delete system32")
    print("Troll Trigger Event:", event)

    # Cast simulated jury votes
    court.record_jury_vote("ViewerA", "!guilty")
    court.record_jury_vote("ViewerB", "!guilty")
    court.record_jury_vote("ViewerC", "!guilty")
    court.record_jury_vote("ViewerD", "!innocent")

    time.sleep(1.05)
    verdict_res = court.resolve_verdict()
    print("\nTrial Verdict Result:", verdict_res)
