from pydantic import BaseModel, Field
from typing import Optional, List

class RateLimits(BaseModel):
    min_delay_seconds: int = 3
    max_delay_seconds: int = 7
    per_hour_cap: int = 25
    per_day_cap: int = 80

class Settings(BaseModel):
    api_id: int
    api_hash: str
    session_name: str
    channel_username: str
    channel_join_link: str
    rate_limits: RateLimits
    templates: List[str] = Field(default_factory=list)

class InboxUser(BaseModel):
    user_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_msg_at: Optional[int] = None  # epoch seconds

class ChannelMember(BaseModel):
    user_id: int
    username: Optional[str] = None

class OutreachResult(BaseModel):
    user_id: int
    template_idx: int
    status: str  # sent/skipped/error
    error: Optional[str] = None