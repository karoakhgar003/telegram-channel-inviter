import asyncio
from typing import AsyncGenerator, Optional

from telethon import TelegramClient
from telethon.tl.types import User
from telethon.errors import FloodWaitError, UserIsBlockedError, ChatWriteForbiddenError
from telethon.errors.rpcerrorlist import UserNotParticipantError, ChannelPrivateError
from telethon.tl.functions.channels import GetParticipantRequest

class TelegramClientService:
    def __init__(self, api_id: int, api_hash: str, session_name: str):
        self.client = TelegramClient(session_name, api_id, api_hash)
        self._channel_entity = None

    async def __aenter__(self):
        await self.client.connect()
        if not await self.client.is_user_authorized():
            # Interactive first-time login
            await self.client.start(
                phone=lambda: input("Enter phone (e.g. +98912...): "),
                code_callback=lambda: input("Enter the code Telegram sent you: "),
                password=lambda: input("Two-step password (if any): ")
            )
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.client.disconnect()

    async def get_channel_entity(self, channel_username_or_link: str):
        """
        Resolve and cache the channel entity (accepts @handle or invite link).
        """
        if self._channel_entity is None:
            self._channel_entity = await self.client.get_entity(channel_username_or_link)
        return self._channel_entity

    async def iter_inbox_users(self) -> AsyncGenerator[User, None]:
        async for dialog in self.client.iter_dialogs():
            ent = dialog.entity
            if isinstance(ent, User) and not ent.is_self:
                yield ent

    async def is_user_in_channel(self, channel_username_or_link: str, user_id: int) -> Optional[bool]:
        """
        Returns True if user is a participant, False if not, and raises if we can't check.
        """
        chan = await self.get_channel_entity(channel_username_or_link)
        try:
            await self.client(GetParticipantRequest(channel=chan, participant=user_id))
            return True
        except UserNotParticipantError:
            return False
        except ChannelPrivateError as e:
            # You must be a member/admin of the channel to check
            raise e

    async def safe_send_message(self, user_id: int, text: str, *, delay_before: Optional[float] = None):
        if delay_before:
            await asyncio.sleep(delay_before)
        try:
            await self.client.send_message(user_id, text)
            return ("sent", None)
        except FloodWaitError as e:
            return ("error", f"FLOOD_WAIT_{e.seconds}s")
        except (UserIsBlockedError, ChatWriteForbiddenError) as e:
            return ("skipped", str(e))
        except Exception as e:
            return ("error", str(e))