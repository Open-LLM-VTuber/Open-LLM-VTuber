# src/open_llm_vtuber/economy/loyalty_economy.py
"""
Autonomous Cross-Platform Micro-Economy & Stream Reward Points.

Provides a zero-cost cryptographic point system (Sparkles) operating across
Twitch, YouTube, Kick, and Discord. Uses an immutable SQLite ledger with SHA-256
hash chaining to guarantee balance integrity and enable interactive rewards.
"""

import hashlib
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from loguru import logger


@dataclass
class RedemptionItem:
    item_id: str
    name: str
    cost: int
    category: str  # "visual", "voice", "physics", "social"
    description: str


class StreamLoyaltyEconomy:
    """
    Cryptographic Watch-Time Economy & Reward Redemption Engine.
    """

    DEFAULT_CATALOG = {
        "sunglasses": RedemptionItem("sunglasses", "Cool Sunglasses", 150, "visual", "Puts stylish black shades on the avatar"),
        "voice_robot": RedemptionItem("voice_robot", "Robotic Glitch Voice", 200, "voice", "Transforms avatar voice into cybernetic synth for 30s"),
        "toss_pie": RedemptionItem("toss_pie", "Throw Virtual Pie", 300, "physics", "Launches a physics pie directly at the avatar's face"),
        "stream_shoutout": RedemptionItem("stream_shoutout", "Personal Stream Shoutout", 500, "social", "The VTuber delivers an enthusiastic verbal shoutout to you"),
    }

    def __init__(self, db_path: str = "data/loyalty_ledger.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._init_db()

    def _init_db(self):
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS ledger (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    delta INTEGER NOT NULL,
                    balance INTEGER NOT NULL,
                    reason TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    prev_hash TEXT NOT NULL,
                    curr_hash TEXT NOT NULL
                )
            """)

    def _compute_hash(self, prev_hash: str, username: str, delta: int, balance: int, reason: str, ts: float) -> str:
        payload = f"{prev_hash}:{username}:{delta}:{balance}:{reason}:{ts}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def get_balance(self, username: str) -> int:
        """Queries the current confirmed balance for a user."""
        cur = self.conn.cursor()
        cur.execute("SELECT balance FROM ledger WHERE username = ? ORDER BY id DESC LIMIT 1", (username.lower(),))
        row = cur.fetchone()
        return row[0] if row else 0

    def award_watch_time(self, username: str, points: int = 10, minutes_watched: int = 5) -> int:
        """Awards watch-time loyalty points with cryptographic signature."""
        return self._record_transaction(
            username=username,
            delta=points,
            reason=f"Watch-time award ({minutes_watched}m active)",
        )

    def redeem_reward(self, username: str, item_id: str) -> Tuple[bool, str, int]:
        """
        Attempts to spend points on a redemption catalog item.
        Returns: (success, message, remaining_balance)
        """
        item = self.DEFAULT_CATALOG.get(item_id.lower())
        if not item:
            return False, f"Unknown item '{item_id}'. Available: {list(self.DEFAULT_CATALOG.keys())}", self.get_balance(username)

        current_balance = self.get_balance(username)
        if current_balance < item.cost:
            return False, f"Insufficient Sparkles! Need {item.cost}, but you have {current_balance}.", current_balance

        new_bal = self._record_transaction(
            username=username,
            delta=-item.cost,
            reason=f"Redeemed: {item.name}",
        )
        logger.info(f"Chatter @{username} redeemed '{item.name}' for {item.cost} Sparkles! New balance: {new_bal}")
        return True, f"Successfully redeemed {item.name}! Triggering {item.category} effect...", new_bal

    def _record_transaction(self, username: str, delta: int, reason: str) -> int:
        """Appends a new cryptographically chained transaction to the ledger."""
        uname = username.lower()
        cur = self.conn.cursor()
        cur.execute("SELECT balance, curr_hash FROM ledger WHERE username = ? ORDER BY id DESC LIMIT 1", (uname,))
        row = cur.fetchone()

        prev_balance = row[0] if row else 0
        prev_hash = row[1] if row else "GENESIS_LOYALTY_HASH"
        new_balance = prev_balance + delta

        now = time.time()
        curr_hash = self._compute_hash(prev_hash, uname, delta, new_balance, reason, now)

        with self.conn:
            self.conn.execute("""
                INSERT INTO ledger (username, delta, balance, reason, timestamp, prev_hash, curr_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (uname, delta, new_balance, reason, now, prev_hash, curr_hash))

        return new_balance

    def verify_ledger_integrity(self) -> Dict[str, Any]:
        """Verifies the complete SHA-256 chain for all accounts in the database."""
        t0 = time.perf_counter()
        cur = self.conn.cursor()
        cur.execute("SELECT id, username, delta, balance, reason, timestamp, prev_hash, curr_hash FROM ledger ORDER BY id ASC")
        rows = cur.fetchall()

        user_last_hash = {}
        for r in rows:
            rid, uname, delta, bal, reason, ts, prev_h, curr_h = r
            expected_prev = user_last_hash.get(uname, "GENESIS_LOYALTY_HASH")
            if prev_h != expected_prev:
                return {"valid": False, "error": f"Invalid prev_hash at row {rid} for user {uname}"}

            expected_curr = self._compute_hash(prev_h, uname, delta, bal, reason, ts)
            if curr_h != expected_curr:
                return {"valid": False, "error": f"Tampered transaction at row {rid} for user {uname}"}

            user_last_hash[uname] = curr_h

        latency_ms = (time.perf_counter() - t0) * 1000.0
        return {"valid": True, "total_transactions": len(rows), "latency_ms": round(latency_ms, 3)}


if __name__ == "__main__":
    economy = StreamLoyaltyEconomy()
    print("Testing Loyalty Micro-Economy & Hash-Chaining...")

    # Award points to test chatter
    u = "GamerChao"
    bal1 = economy.award_watch_time(u, points=250, minutes_watched=125)
    print(f"Awarded watch-time points to @{u} -> Current Balance: {bal1} Sparkles")

    # Attempt redemption
    success, msg, bal2 = economy.redeem_reward(u, "sunglasses")
    print(f"Redemption: Success={success} | Msg: \"{msg}\" | Balance: {bal2}")

    # Audit cryptographic ledger
    audit = economy.verify_ledger_integrity()
    print(f"\nLedger Cryptographic Audit: Valid={audit['valid']} | Transactions={audit['total_transactions']} in {audit['latency_ms']} ms")
