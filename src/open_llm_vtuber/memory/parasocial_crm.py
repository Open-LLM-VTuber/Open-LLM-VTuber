"""
Parasocial CRM & Knowledge Graph Memory for AI Influencers.
Embedded SQLite property store tracking individual chatters, inside jokes, and donation streaks.
"""
import sqlite3
import os
import time
from typing import Optional, Dict, Any, List
from loguru import logger


class ParasocialCRM:
    """
    Sub-millisecond embedded relationship store for live streaming viewers.
    """
    def __init__(self, db_path: str = "data/parasocial_crm.db"):
        os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else ".", exist_ok=True)
        self.db_path = db_path
        self._init_db()

    def _get_conn(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._get_conn() as conn:
            c = conn.cursor()
            c.execute("""
            CREATE TABLE IF NOT EXISTS viewers (
                username TEXT PRIMARY KEY,
                streams_attended INTEGER DEFAULT 1,
                total_tips REAL DEFAULT 0.0,
                nickname TEXT DEFAULT '',
                last_seen REAL
            )
            """)
            c.execute("""
            CREATE TABLE IF NOT EXISTS inside_jokes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                joke_name TEXT,
                context TEXT,
                occurrences INTEGER DEFAULT 1,
                FOREIGN KEY (username) REFERENCES viewers(username)
            )
            """)
            conn.commit()

    def record_interaction(self, username: str, tip_amount: float = 0.0, nickname: str = ""):
        username = username.lower().strip()
        now = time.time()
        with self._get_conn() as conn:
            c = conn.cursor()
            c.execute("SELECT streams_attended, total_tips FROM viewers WHERE username = ?", (username,))
            row = c.fetchone()
            if row:
                streams, tips = row
                c.execute("""
                UPDATE viewers
                SET streams_attended = streams_attended + 1,
                    total_tips = total_tips + ?,
                    last_seen = ?,
                    nickname = CASE WHEN ? != '' THEN ? ELSE nickname END
                WHERE username = ?
                """, (tip_amount, now, nickname, nickname, username))
            else:
                c.execute("""
                INSERT INTO viewers (username, streams_attended, total_tips, nickname, last_seen)
                VALUES (?, 1, ?, ?, ?)
                """, (username, tip_amount, nickname, now))
            conn.commit()

    def add_inside_joke(self, username: str, joke_name: str, context: str):
        username = username.lower().strip()
        self.record_interaction(username)
        with self._get_conn() as conn:
            c = conn.cursor()
            c.execute("SELECT id, occurrences FROM inside_jokes WHERE username = ? AND joke_name = ?", (username, joke_name))
            row = c.fetchone()
            if row:
                c.execute("UPDATE inside_jokes SET occurrences = occurrences + 1, context = ? WHERE id = ?", (context, row[0]))
            else:
                c.execute("INSERT INTO inside_jokes (username, joke_name, context, occurrences) VALUES (?, ?, ?, 1)", (username, joke_name, context))
            conn.commit()
        logger.info(f"ParasocialCRM: Saved inside joke '{joke_name}' for @{username}")

    def get_viewer_context(self, username: str) -> Optional[str]:
        username = username.lower().strip()
        with self._get_conn() as conn:
            c = conn.cursor()
            c.execute("SELECT streams_attended, total_tips, nickname FROM viewers WHERE username = ?", (username,))
            v_row = c.fetchone()
            if not v_row:
                return None

            streams, tips, nick = v_row
            c.execute("SELECT joke_name, context FROM inside_jokes WHERE username = ? ORDER BY occurrences DESC LIMIT 2", (username,))
            jokes = c.fetchall()

            parts = [
                f"[PARASOCIAL VIEWER CRM: @{username}]",
                f"- Streams Attended: {streams}",
                f"- Total Tips: ${tips:.2f}"
            ]
            if nick:
                parts.append(f"- Known Nickname: \"{nick}\"")
            if jokes:
                jokes_str = "; ".join([f"'{j[0]}' ({j[1]})" for j in jokes])
                parts.append(f"- Shared Inside Jokes: {jokes_str}")
                parts.append(f"Directive: Greet @{username} warmly as a returning regular friend and reference their inside joke if appropriate.")
            else:
                parts.append("Directive: Acknowledge @{username} as a returning community member.")

            return "\n".join(parts)
