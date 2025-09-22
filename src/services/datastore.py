import aiosqlite
import os
from pathlib import Path
from typing import Iterable, Tuple, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = str(DATA_DIR / "db.sqlite")

SCHEMA = """
CREATE TABLE IF NOT EXISTS users_inbox (
  user_id INTEGER PRIMARY KEY,
  username TEXT,
  first_name TEXT,
  last_msg_at INTEGER
);

CREATE TABLE IF NOT EXISTS membership_cache (
  user_id INTEGER PRIMARY KEY,
  is_member INTEGER NOT NULL,
  checked_at INTEGER
);

CREATE TABLE IF NOT EXISTS channel_members (
  user_id INTEGER PRIMARY KEY,
  username TEXT,
  first_seen_at INTEGER,
  last_seen_at INTEGER
);

CREATE TABLE IF NOT EXISTS outreach_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER,
  template_idx INTEGER,
  sent_at INTEGER,
  status TEXT,
  error TEXT
);

CREATE TABLE IF NOT EXISTS do_not_contact (
  user_id INTEGER PRIMARY KEY,
  reason TEXT,
  added_at INTEGER
);

CREATE TABLE IF NOT EXISTS checkpoints (
  key TEXT PRIMARY KEY,
  value TEXT
);
"""

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(SCHEMA)
        await db.commit()

async def upsert_inbox_users(rows: Iterable[Tuple[int, str, str, int]]):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executemany(
            """
            INSERT INTO users_inbox(user_id, username, first_name, last_msg_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username=excluded.username,
                first_name=excluded.first_name,
                last_msg_at=excluded.last_msg_at
            """,
            rows,
        )
        await db.commit()

async def membership_cached(user_id: int) -> Optional[bool]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT is_member FROM membership_cache WHERE user_id=?", (user_id,)) as cur:
            row = await cur.fetchone()
            if row is None:
                return None
            return bool(row[0])

async def cache_membership(user_id: int, is_member: bool, checked_at: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO membership_cache(user_id, is_member, checked_at)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
              is_member=excluded.is_member,
              checked_at=excluded.checked_at
            """,
            (user_id, int(is_member), checked_at),
        )
        await db.commit()        

async def upsert_channel_members(rows: Iterable[Tuple[int, str, int, int]]):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executemany(
            """
            INSERT INTO channel_members(user_id, username, first_seen_at, last_seen_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username=excluded.username,
                last_seen_at=excluded.last_seen_at
            """,
            rows,
        )
        await db.commit()

async def already_messaged_user_ids() -> set[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT DISTINCT user_id FROM outreach_log WHERE status='sent'") as cur:
            return {row[0] for row in await cur.fetchall()}

async def dnc_user_ids() -> set[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id FROM do_not_contact") as cur:
            return {row[0] for row in await cur.fetchall()}

async def inbox_user_ids() -> set[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id FROM users_inbox") as cur:
            return {row[0] for row in await cur.fetchall()}

async def channel_member_ids() -> set[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id FROM channel_members") as cur:
            return {row[0] for row in await cur.fetchall()}

async def log_outreach(user_id: int, template_idx: int, status: str, sent_at: int, error: str | None = None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO outreach_log(user_id, template_idx, sent_at, status, error) VALUES (?, ?, ?, ?, ?)",
            (user_id, template_idx, sent_at, status, error),
        )
        await db.commit()

async def save_checkpoint(key: str, value: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO checkpoints(key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )
        await db.commit()

async def load_checkpoint(key: str) -> str | None:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT value FROM checkpoints WHERE key=?", (key,)) as cur:
            row = await cur.fetchone()
            return row[0] if row else None