"""Stored chat message type."""
from typing import Literal, TypedDict


class ChatMessage(TypedDict):
    role: Literal["user", "assistant"]
    content: str
    created_at: str
