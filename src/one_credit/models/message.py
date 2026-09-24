from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MessageType(str, Enum):
    REQUEST = "REQUEST"
    PROPOSAL = "PROPOSAL"
    COUNTEROFFER = "COUNTEROFFER"
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"
    AGREEMENT = "AGREEMENT"


class Message(BaseModel):
    """Direct peer-to-peer communication between agents."""

    model_config = ConfigDict(extra="ignore")

    message_id: str
    sender: str
    receiver: str
    message_type: MessageType | str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    payload: dict[str, Any] = Field(default_factory=dict)

    @field_validator("message_id", "sender", "receiver")
    @classmethod
    def validate_non_empty(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("must not be blank")
        return cleaned

    @field_validator("message_type", mode="before")
    @classmethod
    def normalize_message_type(cls, value: Any) -> str:
        if isinstance(value, MessageType):
            return value.value
        if isinstance(value, str):
            cleaned = value.strip().upper()
            if cleaned in {member.value for member in MessageType}:
                return cleaned
        raise ValueError("message_type must be one of REQUEST, PROPOSAL, COUNTEROFFER, ACCEPT, REJECT, AGREEMENT")
