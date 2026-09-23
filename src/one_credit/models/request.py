from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Request(BaseModel):
    """A user request that may be fulfilled by one or more agents."""

    model_config = ConfigDict(extra="ignore")

    id: str
    title: str = Field(..., min_length=1)
    description: str = ""
    requester_id: str
    required_resources: list[str] = Field(default_factory=list)
    priority: str = "normal"
    status: str = "open"
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("title must not be blank")
        return cleaned

    @field_validator("requester_id")
    @classmethod
    def validate_requester_id(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("requester_id must not be blank")
        return cleaned

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("priority must not be blank")
        return cleaned.lower()
