import time
from typing import List, Tuple
from telethon.tl.types import User

from src.services.telegram_client import TelegramClientService
from src.services import datastore

async def collect_inbox(api_id: int, api_hash: str, session: str) -> int:
    await datastore.init_db()
    rows: List[Tuple[int, str | None, str | None, int]] = []
    async with TelegramClientService(api_id, api_hash, session) as tg:
        async for u in tg.iter_inbox_users():
            rows.append((u.id, getattr(u, 'username', None), getattr(u, 'first_name', None), int(time.time())))
    await datastore.upsert_inbox_users(rows)
    return len(rows)

async def collect_channel_members(api_id: int, api_hash: str, session: str, channel_username: str) -> int:
    await datastore.init_db()
    ts = int(time.time())
    rows: List[Tuple[int, str | None, int, int]] = []
    async with TelegramClientService(api_id, api_hash, session) as tg:
        async for u in tg.iter_channel_members(channel_username):
            rows.append((u.id, getattr(u, 'username', None), ts, ts))
    await datastore.upsert_channel_members(rows)
    return len(rows)