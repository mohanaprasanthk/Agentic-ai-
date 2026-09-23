from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Proposal(BaseModel):
    """A proposed response to a request from a specific agent."""

    model_config = ConfigDict(extra="ignore")

    id: str
    request_id: str
    agent_id: str
    summary: str = Field(..., min_length=1)
    price: float | None = None
    estimated_duration: str | None = None
    status: str = "pending"
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("request_id")
    @classmethod
    def validate_request_id(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("request_id must not be blank")
        return cleaned

    @field_validator("agent_id")
    @classmethod
    def validate_agent_id(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("agent_id must not be blank")
        return cleaned

    @field_validator("summary")
    @classmethod
    def validate_summary(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("summary must not be blank")
        return cleaned
