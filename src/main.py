import asyncio, json, os
from pathlib import Path

from src.models import Settings
from src.services import datastore
from src.workflows.collector import collect_inbox, collect_channel_members
from src.workflows.outreach import send_outreach

CONFIG_PATH = Path("config/settings.json")

def load_settings() -> Settings:
    with open(CONFIG_PATH, encoding="utf-8-sig") as f:
        data = json.load(f)
    return Settings(**data)

async def cmd_collect_inbox(cfg: Settings):
    n = await collect_inbox(cfg.api_id, cfg.api_hash, cfg.session_name)
    print(f"Collected inbox users: {n}")

async def cmd_collect_members(cfg: Settings):
    n = await collect_channel_members(cfg.api_id, cfg.api_hash, cfg.session_name, cfg.channel_username)
    print(f"Collected channel members: {n}")

async def cmd_outreach(cfg: Settings, dry_run: bool = False):
    await datastore.init_db()
    v = cfg.rate_limits
    count = await send_outreach(
        cfg.api_id,
        cfg.api_hash,
        cfg.session_name,
        templates=cfg.templates,
        channel_link=cfg.channel_join_link,          # used in message body
        rl_min=v.min_delay_seconds,
        rl_max=v.max_delay_seconds,
        per_hour_cap=v.per_hour_cap,
        per_day_cap=v.per_day_cap,
        dry_run=dry_run,
        channel_username_or_link=cfg.channel_username or cfg.channel_join_link  # <-- add this
    )
    print(("DRY-RUN sent" if dry_run else "Sent"), count)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Telegram Outreach Manager")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("collect-inbox")
    sub.add_parser("collect-members")

    p_send = sub.add_parser("send")
    p_send.add_argument("--dry", action="store_true", help="Do not send, just log")

    args = parser.parse_args()
    cfg = load_settings()

    if args.cmd == "collect-inbox":
        asyncio.run(cmd_collect_inbox(cfg))
    elif args.cmd == "collect-members":
        asyncio.run(cmd_collect_members(cfg))
    elif args.cmd == "send":
        asyncio.run(cmd_outreach(cfg, dry_run=args.dry))