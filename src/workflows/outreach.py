# src/workflows/outreach.py
import asyncio, random, time
from src.services import datastore
from src.services.messaging import rotate_template, render_message
from src.services.telegram_client import TelegramClientService
from src.services.utils import Throttler

async def iter_targets_by_membership(api_id: int, api_hash: str, session: str, channel_username_or_link: str):
    """
    Yield user_ids who messaged us but are NOT in the channel (checked by ID).
    Uses cache to avoid unnecessary API calls.
    """
    inbox = await datastore.inbox_user_ids()
    sent = await datastore.already_messaged_user_ids()
    dnc = await datastore.dnc_user_ids()

    candidates = list(inbox - sent - dnc)
    random.shuffle(candidates)

    async with TelegramClientService(api_id, api_hash, session) as tg:
        # Make sure we can resolve the channel entity once
        await tg.get_channel_entity(channel_username_or_link)

        for uid in candidates:
            cached = await datastore.membership_cached(uid)
            if cached is not None:
                if not cached:
                    yield uid
                continue

            # Not cached; check via channels.getParticipant
            try:
                member = await tg.is_user_in_channel(channel_username_or_link, uid)
            except Exception as e:
                # If we cannot check (e.g., channel private and you’re not a member), skip safely
                # You could log this case if desired
                continue

            await datastore.cache_membership(uid, bool(member), int(time.time()))
            if not member:
                yield uid

async def send_outreach(
    api_id: int,
    api_hash: str,
    session: str,
    *,
    templates: list[str],
    channel_link: str,
    rl_min: int,
    rl_max: int,
    per_hour_cap: int,
    per_day_cap: int,
    dry_run: bool = False,
    channel_username_or_link: str | None = None,
):
    if channel_username_or_link is None:
        # Default to channel_link (works for public links and invite links)
        channel_username_or_link = channel_link

    throttler = Throttler(rl_min, rl_max)
    hourly_sem = asyncio.Semaphore(per_hour_cap)
    daily_sem = asyncio.Semaphore(per_day_cap)

    # Build the target stream based on membership checks
    targets = []
    async for uid in iter_targets_by_membership(api_id, api_hash, session, channel_username_or_link):
        targets.append(uid)

    async with TelegramClientService(api_id, api_hash, session) as tg:
        template_idx = 0
        sent_count = 0
        for uid in targets:
            if daily_sem.locked():
                break
            async with daily_sem:
                async with hourly_sem:
                    _, tpl = rotate_template(templates, template_idx)
                    template_idx += 1
                    text = render_message(tpl, {"first_name": "", "channel_link": channel_link})

                    if dry_run:
                        await datastore.log_outreach(uid, template_idx - 1, "dry_run", int(time.time()))
                        await throttler.sleep()
                        continue

                    status, error = await tg.safe_send_message(uid, text)
                    await datastore.log_outreach(uid, template_idx - 1, status, int(time.time()), error)
                    sent_count += 1
                    await throttler.sleep()
        return sent_count
